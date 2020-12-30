As of ``{{ music_summ.current_date_string}}``, there are {{ music_summ.num_songs }} songs made by {{ music_summ.num_artists }} artists in {{ music_summ.num_albums }} albums. The total size of music media is {{ music_summ.formatted_size }}. The total duration of music media is {{ music_summ.formatted_duration }}.
{% if music_summ.len_datas_since > 0 %}
Since ``{{ music_summ.since_date_string }}``, I have added {{ music_summ.num_songs_since }} songs made by {{ music_summ.num_artists_since }} artists in {{ music_summ.num_albums_since}} albums. The total size of music media that I have added is {{ music_summ.formatted_size_since}}. The total duration of music media that I have added is {{ music_summ.formatted_duration_since }}.
{% endif %}
