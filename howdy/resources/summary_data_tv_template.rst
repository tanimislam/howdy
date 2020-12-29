As of {{ tv_summ.current_date_string}}, there are {{ tv_summ.num_episodes }} TV episodes in {{ tv_summ.num_shows }} TV shows. The total size of TV media is {{ tv_summ.formatted_size }}. The total duration of TV media is {{ tv_summ.formatted_duration }}.
{% if tv_summ.len_datas_since > 0 %}
Since {{ tv_summ.since_date_string }}, I have added {{ tv_summ.num_episodes_since }} TV epsisodes in {{ tv_summ.num_shows_since }} TV shows. The total size of TV media that I have added is {{ tv_summ.formatted_size_since}}. The total duration of TV media that I have added is {{ tv_summ.formatted_duration_since }}.
{% endif %}
