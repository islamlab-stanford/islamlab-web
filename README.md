# islamlab.org

Source for the **Islam Lab** website — a projects hub for the lab's open research, models, and tools. A static site served on **GitHub Pages** at **[islamlab.org](https://islamlab.org)**.

> The lab's official page is at Stanford Medicine: <https://med.stanford.edu/islam-lab.html>. This site collects our open projects.

## Live

- **Home** — https://islamlab.org
- **Jeus** — https://islamlab.org/jeus · an AI agent for biomedical data analysis: a two-minute explainer, the manuscript's worked examples and headline results
- **Graph-in-Graph** — https://islamlab.org/gig · patient-specific pathway graphs for transcriptomic prediction
- **Dynomap** — https://islamlab.org/dynomap · task-adaptive spatial representations for biomedical tabular data
- **Graph2Image** — https://islamlab.org/graph2image · semantic cartography for biological networks
- **Graph Foundation Model** — https://islamlab.org/graph-foundation-model · transferable structural representations across heterogeneous graphs
- **scVision** — https://islamlab.org/scvision · a vision foundation model for single-cell biology

## Structure

```
index.html          # Home (projects hub)
jeus/               # Jeus project page: the manuscript's worked examples and headline results
  index.html
  style.css
  interactive.js
  assets/           # examples.js, results.js (built from the manuscript's records), og.png,
                    # the explainer video (jeus_explainer.mp4, its poster and captions)
  video/            # how the explainer is made: script.json, narrate.py, scenes.py, build.py
scvision/           # scVision project page
  index.html
  style.css
  assets/fig1.png
dynomap/            # Dynomap project page
  index.html
  style.css
  interactive.js
  assets/
graph2image/        # Graph2Image project page
  index.html
  styles.css
  app.js
  public/assets/
graph-foundation-model/ # Graph Foundation Model app, served separately at this path
gig/                # Graph-in-Graph public project page
CNAME               # Custom domain: islamlab.org
.nojekyll           # Serve files as-is (no Jekyll)
```


## Credits

Islam Lab · Department of Radiation Oncology, Stanford University School of Medicine.
Contact: [tauhid@stanford.edu](mailto:tauhid@stanford.edu)
