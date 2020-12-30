As of ``{{ movie_summ.current_date_string}}``, there are {{ movie_summ.num_movies }} movies in {{ movie_summ.num_categories }} categories. The total size of movie media is {{ movie_summ.formatted_size }}. The total duration of movie media is {{ movie_summ.formatted_duration }}.{% if movie_summ.len_datas_since > 0 %}
Since ``{{ movie_summ.since_date_string }}``, I have added {{ movie_summ.num_movies_since }} movies in {{ movie_summ.num_categories_since }} categories. The total size of movie media that I have added is {{ movie_summ.formatted_size_since}}. The total duration of movie media that I have added is {{ movie_summ.formatted_duration_since }}.{% endif %}
{% if last_N_movies|length > 0 %}
Here are the {{ last_N_movies|length }} movies I have most recently added.

{% for movie in last_N_movies -%}
* {% if movie.hasURL %}`{{ movie.name }} ({{ movie.year }}) <{{ movie.url }}>`_,{% else %}{{ movie.name }} ({{ movie.year }}),{% endif %} added on {{ movie.added_date_string }}.
{% endfor %}{% endif %}
Here is a summary by category.
{% for entry in catmovs %}
* **{{ entry.category }}**: {{ entry.description }}
{% endfor %}
