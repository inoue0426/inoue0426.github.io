---
permalink: /
title: "About"
author_profile: true
redirect_from: 
  - /about/
  - /about.html
---

I am Yoshitaka Inoue, a PhD candidate in Computer Science at the University of Minnesota under the supervision of [Dr. Rui Kuang](https://cse.umn.edu/cs/rui-kuang). I am also a pre-doctoral fellow at the National Library of Medicine and affiliated with the National Cancer Institute, advised by [Dr. Augustin Luna](https://www.nlm.nih.gov/research/researchstaff/LunaAugustin.html).

I am interested in graph neural networks, drug discovery, single cell analysis, and biological networks. My future goal is to understand biological phenomena using computational approaches and to contribute to the development of therapeutics through my research.

I hold an M.S. in Information Science from the Nara Institute of Science and Technology, where I was advised by [Dr. Shigehiko Kanaya](https://isw3.naist.jp/Research/ai-csb-en.html).  During my master's degree, I studied abroad at UC Davis under the supervision of [Dr. Oliver Fiehn](https://fiehnlab.ucdavis.edu/staff/fiehn).

## Publications Snapshot

{% assign pub_count = site.publications | size %}
{% assign latest_pub = site.publications | sort: "year" | last %}

- Total publications: **{{ pub_count }}**
{% if latest_pub %}
- Latest publication year: **{{ latest_pub.year | default: latest_pub.date | date: "%Y" }}**
{% endif %}

## Recent Publications

{% assign recent_pubs = site.publications | sort: "year" | reverse %}
{% for post in recent_pubs limit:5 %}
  {% assign paper_link = post.paperurl %}
  {% if paper_link == nil and post.url and post.url contains '://' %}
    {% assign paper_link = post.url %}
  {% endif %}
  {% assign display_authors = post.authors | default: "" | replace: "Yoshitaka Inoue", "**Yoshitaka Inoue**" %}

- {{ post.title }} ({{ post.year | default: post.date | date: "%Y" }})  
  {{ display_authors }}{% if paper_link %} · [Paper]({{ paper_link }}){% endif %}
{% endfor %}
