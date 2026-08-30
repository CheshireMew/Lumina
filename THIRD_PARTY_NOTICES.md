# Third-party notices

Lumina depends on third-party libraries, runtimes, models, and media. Those materials keep their own licenses and are not relicensed by Lumina's GPL license.

## Live2D Cubism

`public/libs/live2dcubismcore.min.js` and other Cubism SDK/runtime components are governed by Live2D's terms, not Lumina's GPL:

- https://www.live2d.com/eula/live2d-free-material-license-agreement_en.html
- https://www.live2d.com/eula/live2d-proprietary-software-license-agreement_en.html

## Hiyori sample model

`public/live2d/Hiyori/**` is a Live2D sample model and remains governed by the Live2D Sample Model Terms:

- https://www.live2d.com/eula/live2d-sample-model-terms_en.html
- https://www.live2d.com/en/learn/sample/momose-hiyori-video/

## Open-source dependencies

`public/libs/pixi-live2d-display-cubism4.min.js` is built from `pixi-live2d-display`. JavaScript and Python dependencies installed from the project manifests retain the license supplied by each package. Their package metadata and bundled license files are the authoritative notices for the installed versions.

Runtime data under `brain/`, `data/`, `Lumina_Data/`, and `python_backend/characters/*/data/` is user or application data. It is not GPL-licensed source merely because it may exist beside the repository during development.
