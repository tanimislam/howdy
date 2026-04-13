import os, sys, glob, logging, subprocess, json, time, uuid
from pathos.multiprocessing import Pool, cpu_count
from shutil import which, move

def _find_exec( exec_name = 'ffmpeg' ):
    which_exec = which( exec_name )
    if which_exec is None: return None
    #
    ## now check if we can execute on it
    if os.access( which_exec, os.X_OK ): return which_exec
    #
    ## otherwise look in /usr/bin
    which_exec = which( exec_name, path='/usr/bin')
    if which_exec is None: return None
    if os.access( which_exec, os.X_OK ): return which_exec
    return None

_ffmpeg_exec      = _find_exec( 'ffmpeg' )
_ffprobe_exec     = _find_exec( 'ffprobe' )
_mkvpropedit_exec = _find_exec( 'mkvpropedit' )
_nice_exec        = _find_exec( 'nice' )

def get_fnames_from_directories( directory_names ):
    fnames = sorted(set(
        chain.from_iterable(map(
            lambda directory_name:
            glob.glob( os.path.join( directory_name, '*.mp4'  ) ) +
            glob.glob( os.path.join( directory_name, '*.mkv'  ) ) +
            glob.glob( os.path.join( directory_name, '*.webm' ) ) +
            glob.glob( os.path.join( directory_name, '*.m4v'  ) ), directory_names ) ) ) )
    return fnames


def get_ffprobe_json( filename ):
    """
    Uses FFProbe_ to get statistics on media file and dumping into a :py:class:`dict`.

    :param str filename: the input media file.
    :returns: a :py:class:`dict` of statistics on the media file, which includes video stream bitrate and duration, the bitrate and duration of each audio track, and summaries of each subtitle track.

    For example, here is the output when running on the MKV_ media file of `Star Trek VI: The Undiscovered Country <https://en.wikipedia.org/wiki/Star_Trek_VI:_The_Undiscovered_Country>`_ that I have,

    .. code-block:: python

       {'is_hevc': False,
        'bit_rate_kbps': 929.4638671875,
        'audio_bit_rate_kbps': 93.4990234375}

    My media file is not HEVC_ encoded.
    
    :rtype: dict

    .. _FFProbe: https://ffmpeg.org/ffprobe.html
    """
    assert( _ffprobe_exec is not None )
    stdout_val = subprocess.check_output(
        [ _ffprobe_exec, '-v', 'quiet', '-show_streams',
         '-show_format', '-print_format', 'json', filename ],
        stderr = subprocess.STDOUT )
    file_info = json.loads( stdout_val )
    return file_info

def is_hevc( filename ):
    """
    Checks whether the video codec is HEVC_ (also called H265).

    :param str filename: the input media video file.
    :return: ``True`` if the video stream codec is HEVC_, ``False`` otherwise.
    :rtype: bool

    .. _HEVC: https://en.wikipedia.org/wiki/High_Efficiency_Video_Coding
    
    .. seealso::

       * :py:meth:`get_ffprobe_json <howdy.core.core_ffmpeg.get_ffprobe_json>`
    """
    data = get_ffprobe_json( filename )
    return data['streams'][0]['codec_name'].lower( ) == 'hevc'

def get_hevc_bitrate( filename ):
    """
    This is a confusing function, because this returns a :py:class:`dict` that contains the audio and video stream bitrates *and* status on whether a video media file is HEVC_ encoded.

    :param str filename: the input media video file.
    :returns: the :py:class:`dict` that contains the 
    """
    
    try:
        data = get_ffprobe_json( filename )
        info = {
            'is_hevc' :  data['streams'][0]['codec_name'].lower( ) == 'hevc',
            'bit_rate_kbps' : float( data['format']['bit_rate' ] ) / 1_024, }
        audio_streams = list(filter(lambda entry: entry['codec_type'] == 'audio', data['streams'] ) )
        try:
            bit_rate_audio_1 = sum(map(lambda entry: float( entry[ 'bit_rate' ] ) / 1_024, audio_streams ) )
        except Exception as e:
            bit_rate_audio_1 = 0
        try:
            bit_rate_audio_2 = sum(map(lambda entry: float( entry[ 'tags']['BPS'] ) / 1_024, audio_streams ) )
        except Exception as e:
            bit_rate_audio_2 = 0
        info[ 'audio_bit_rate_kbps' ] = max( bit_rate_audio_1, bit_rate_audio_2 )
        return info
    except Exception as e:
        logging.error( 'PROBLEM WITH %s. ERROR MESSAGE = %s.' % (
            os.path.realpath( filename ), str( e ) ) )
        return None

def find_files_to_process( fnames, do_hevc = True, min_bitrate = 2_000 ):
    """
    Determines those video media files to select, that have a minimum total (video + all audio streams) bit rate above a threshold.

    :param list fnames: the collection of video media files to process.
    :param bool do_hevc: if ``True``, then only process HEVC_ encoded video media files in ``fnames``. If ``False``, then select on *all* video media files in ``fnames``.
    :param int min_bitrate: the *minimum* total bitrate, in kbps, of files to select. Default is 2000 kbps.
    :returns: a :py:class:`dict` of files to choose. Each key is the filename, and its value is the :py:class:`dict` returned by :py:meth:`get_hevc_bitrate <howdy.core.core_ffmpeg.get_hevc_bitrate>` operating on that file.
    :rtype: dict

    .. seealso::

       * :py:meth:`get_hevc_bitrate <howdy.core.core_ffmpeg.get_hevc_bitrate>`
    """
    with Pool( processes = cpu_count( ) ) as pool:
        list_of_files_hevc_br = list(filter(
            lambda tup: tup[1] is not None and tup[1]['bit_rate_kbps'] >= min_bitrate,
            pool.map(lambda fname: ( fname, get_hevc_bitrate( fname ) ), fnames ) ) )
        if not do_hevc:
            list_of_files_hevc_br = list(filter(lambda tup: tup[1]['is_hevc'] == False,
                                                list_of_files_hevc_br ) )
        return dict( list_of_files_hevc_br )


#
## process single file to lower audio bitrate alone
def process_single_filename_lower_audio( filename, newfile, audio_bit_rate_new = 160 ):
    r"""
    Uses FFMpeg_ to lower the file name's audio stream to newer audio bit rate, in kbps. This applies to every audio stream in the file. Also if the media file is an MKV_, uses mkvpropedit_ to add audio and video statistics metadata to the MKV_ file.

    :param str filename: the initial media file (must be MKV_ or MP4_) to process.
    :param str newfile: the new media file (must be MKV_ or MP4_) to process. the extension for ``newfile`` must be the *same* as the extension for ``filename``.
    :param int audio_bit_rate_new: the new per-audio-stream bit rate, in kbps. Must be :math:`\ge 10` kbps.

    .. _FFMpeg: https://en.wikipedia.org/wiki/FFmpeg
    .. _MKV: https://en.wikipedia.org/wiki/Matroska
    .. _MP4: https://en.wikipedia.org/wiki/MP4_file_format
    .. _mkvpropedit: https://mkvtoolnix.download/doc/mkvpropedit.html
    """
    assert( audio_bit_rate_new > 10 )
    assert( _ffmpeg_exec is not None )
    if newfile.endswith( '.mkv' ):
        assert( _mkvpropedit_exec is not None )
    logging.debug( 'FILENAME = %s, NEWFILE = %s, NEW AUDIO BIT RATE = %d.' % (
        filename, newfile, audio_bit_rate_new ) )
    if _nice_exec is not None:
        stdout_val = subprocess.check_output([
            _nice_exec, '-n', '19',
            _ffmpeg_exec, '-y', '-i', 'file:%s' % filename,
            '-vcodec', 'copy',
            '-scodec', 'copy',
            '-acodec', 'aac', '-ab', '%dk' % audio_bit_rate_new,
            'file:%s' % newfile ], stderr = subprocess.PIPE )
    else:
        stdout_val = subprocess.check_output([
            _ffmpeg_exec, '-y', '-i', 'file:%s' % filename,
            '-vcodec', 'copy',
            '-scodec', 'copy',
            '-acodec', 'aac', '-ab', '%dk' % audio_bit_rate_new,
            'file:%s' % newfile ], stderr = subprocess.PIPE )
    logging.debug( stdout_val.decode( 'utf8' ) )
    if newfile.endswith( '.mkv' ):
        if _nice_exec is not None:
            stdout_val = subprocess.check_output([
                _nice_exec, '-n', '19', _mkvpropedit_exec,
                newfile, '--add-track-statistics-tags' ], stderr = subprocess.PIPE )
        else:
            stdout_val = subprocess.check_output([
                _mkvpropedit_exec,
                newfile, '--add-track-statistics-tags' ], stderr = subprocess.PIPE )
        logging.debug( stdout_val.decode( 'utf8' ) )

def process_multiple_files_lower_audio(
    file_names, min_audio_bit_rate = 256, new_audio_bit_rate = 160,
    temp_dir = os.getcwd( ) ):
    """
    Processes a :py:class:`list` of files, whose per-stream audio bit rates are *greater* than some threshold bit rate, down to a new and lower audio bit rate.

    :param list file_names: the collection of video media files to process.
    :param int min_audio_bit_rate: the threshold audio bit rate, in kbps, to process a video media file.
    :param int new_audio_bit_rate: the *new* audio bit rate, in kbps, of audio streams in each file that we process.
    :param str temp_dir: the *temporary* directory into which to store temporary files. Default is the current working directory.
    :returns: a status :py:class:`dict` that contains the number of unique video media files it checked, and the number of unique video files it processed.
    :rtype: dict

    .. seealso::

       * :py:meth:`process_single_filename_lower_audio <howdy.core.core_ffmpeg.process_single_filename_lower_audio>`
    """
    #
    assert( os.path.isdir( os.path.realpath( temp_dir ) ) )
    act_file_names = sorted(filter(
        os.path.isfile, set(map(os.path.realpath, file_names))))
    fnames_dict = dict(filter(lambda entry: entry[1][ 'audio_bit_rate_kbps' ] > min_audio_bit_rate, find_files_to_process(
        act_file_names, do_hevc = True, min_bitrate = 0 ).items( ) ) )
    time00 = time.perf_counter( )
    logging.info( 'found %02d files with audio sizes > %d kbps. Will lower audio bit rate to %d kbps.' % (
        len( fnames_dict ), min_audio_bit_rate, new_audio_bit_rate ) )
    for idx, filename in enumerate(sorted( fnames_dict ) ):
        time0 = time.perf_counter( )
        newfile = os.path.join(
            os.path.realpath( temp_dir ),
            '%s-%s' % ( str( uuid.uuid4( ) ).split('-')[0].strip( ), os.path.basename( filename ).replace(":", "-" ) ) )
        #
        process_single_filename_lower_audio( filename, newfile, new_audio_bit_rate )
        #
        os.chmod(newfile, 0o644 )
        move( newfile, filename )
        dt0 = time.perf_counter( ) - time0
        logging.info( 'processed file %02d / %02d in %0.3f seconds' % (
            idx + 1, len( fnames_dict ), dt0 ) )
    dt00 = time.perf_counter( ) - time00
    logging.info( 'took %0.3f seconds to process %d files' % (
        dt00, len( fnames_dict ) ) )
    return { 'num total files' : len( act_file_names ), 'num files processed' : len( fnames_dict ) }
