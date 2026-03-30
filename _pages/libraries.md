---
layout: archive
title: "Libraries"
permalink: /libraries/
author_profile: true
---

A collection of open-source libraries and tools I have developed for computational biology, drug discovery, and bioinformatics.

## Research Models

{% for lib in site.data.libraries.research %}
### [{{ lib.name }}]({{ lib.github }})

{{ lib.description }}

- **Language:** {{ lib.language }}
- **Topics:** {{ lib.topics }}
- **GitHub:** [{{ lib.github }}]({{ lib.github }}){% if lib.paper %}
- **Paper:** [{{ lib.paper }}]({{ lib.paper }}){% endif %}

{% endfor %}

## Utility Libraries

{% for lib in site.data.libraries.utilities %}
### [{{ lib.name }}]({{ lib.github }})

{{ lib.description }}

- **Language:** {{ lib.language }}
- **Topics:** {{ lib.topics }}
- **GitHub:** [{{ lib.github }}]({{ lib.github }})

{% endfor %}
