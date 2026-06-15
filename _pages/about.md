---
permalink: /
title: "About"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---

I am Yoshitaka Inoue, a PhD candidate in Computer Science at the University of Minnesota advised by [Dr. Rui Kuang](https://cse.umn.edu/cs/rui-kuang). I am also a pre-doctoral fellow at the National Library of Medicine and affiliated with the National Cancer Institute, advised by [Dr. Augustin Luna](https://www.nlm.nih.gov/research/researchstaff/LunaAugustin.html).

My research focuses on graph neural networks for drug discovery, single-cell analysis, and biological network modeling. I aim to develop computational methods that advance translational research and therapeutic development.

I hold an M.S. in Information Science from the Nara Institute of Science and Technology, advised by [Dr. Shigehiko Kanaya](https://isw3.naist.jp/Research/ai-csb-en.html). During my master's, I studied abroad at UC Davis under [Dr. Oliver Fiehn](https://fiehnlab.ucdavis.edu/staff/fiehn).

## Selected Publications

{% assign recent_pubs = site.publications | sort: "year" | reverse %}
{% assign shown_count = 0 %}
{% for post in recent_pubs %}
  {% assign author_list = post.authors | default: "" | split: ", " %}
  {% if author_list[0] == "Yoshitaka Inoue" and shown_count < 5 %}
  {% assign paper_link = post.paperurl %}
  {% if paper_link == nil and post.url and post.url contains '://' %}
    {% assign paper_link = post.url %}
  {% endif %}
  {% assign display_authors = post.authors | default: "" | replace: "Yoshitaka Inoue", "**Yoshitaka Inoue**" %}
  {% if post.year %}
{% assign display_year = post.year %}
  {% else %}
{% assign display_year = post.date | date: "%Y" %}
  {% endif %}
- {{ post.title }} ({{ display_year }}){% if paper_link %} · [Paper]({{ paper_link }}){% endif %}<br>
  {{ display_authors }}
  {% assign shown_count = shown_count | plus: 1 %}
  {% endif %}

{% endfor %}
