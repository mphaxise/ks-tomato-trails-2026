# Garden CV / ML Projects

Review date: 2026-03-07

This note lists open-source repositories and adjacent commercial products relevant to:

- plant, pot, or plot segmentation from images
- growth tracking over time
- disease detection
- fruit detection and counting
- outdoor plant / weed segmentation

The strongest open-source options are mostly framed as plant phenotyping or precision agriculture rather than home gardening, but they are directly relevant to this project.

## Best Fits For This Project

If the immediate goal is indoor tomato pots now and outdoor plots later, the best starting points are:

1. [PlantCV](https://github.com/danforthcenter/plantcv) for classical CV workflows, masks, measurements, and fast experimentation.
2. [AgML](https://github.com/Project-AgML/AgML) for dataset discovery, training pipelines, and reusable agricultural ML benchmarks.
3. [tomatOD](https://github.com/up2metric/tomatOD) for tomato fruit localization and ripeness classes.
4. [OpenWeedLocator](https://github.com/geezacoleman/OpenWeedLocator) for outdoor vegetation segmentation logic and weed-style detection patterns.
5. [Easy-Leaf-Area](https://github.com/heaslon/Easy-Leaf-Area) for simple image-based leaf area tracking in controlled photos.

## Important Gap

I did not find a strong, widely used open-source repo dedicated to indoor home-garden `pot identification` from RGB photos.

For this project, pot identification is likely a custom instance-segmentation or object-detection task built on top of:

- PlantCV for classical masking and contour workflows
- AgML for training data patterns and model scaffolding
- a custom labeled dataset from this repository's tomato pot photos

## Open-Source Repositories

| Project | Repo | Best for | Indoor / Outdoor | Notes |
|---|---|---|---|---|
| PlantCV | [danforthcenter/plantcv](https://github.com/danforthcenter/plantcv) | Plant segmentation, leaf masks, morphology, growth proxy measurement | both | Best general-purpose plant image analysis toolkit in the list. Good first stop for indoor pot photos. |
| AgML | [Project-AgML/AgML](https://github.com/Project-AgML/AgML) | Dataset access, training pipelines, classification, detection, segmentation | both | Includes useful public datasets such as `plant_seedlings_aarhus`, `fruit_detection_worldwide`, `leaf_counting_denmark`, and weed segmentation sets. |
| OpenWeedLocator | [geezacoleman/OpenWeedLocator](https://github.com/geezacoleman/OpenWeedLocator) | Outdoor vegetation segmentation, weed detection, low-cost OpenCV pipelines | outdoor | Strong reference for RGB thresholding, contouring, and practical field camera workflows. |
| tomatOD | [up2metric/tomatOD](https://github.com/up2metric/tomatOD) | Tomato fruit detection, localization, ripeness classes, counting | greenhouse / outdoor-like crop scenes | Directly relevant once the project shifts from seedling tracking to fruit counting. |
| FarmBot org | [farmbot](https://github.com/farmbot) | Camera-assisted garden automation, weed detection, plant growth tracking | both | Open-source garden robotics platform; relevant as a system reference more than a drop-in vision library. |
| FarmBot Web App | [FarmBot/Farmbot-Web-App](https://github.com/FarmBot/Farmbot-Web-App) | Garden automation interface, device control, observation workflows | both | Useful if this project later grows into a camera + actuator workflow. |
| FarmBot OS | [FarmBot/farmbot_os](https://github.com/FarmBot/farmbot_os) | On-device robot software for camera-enabled garden automation | both | Relevant if the project later becomes hardware-integrated. |
| Phenomenal | [openalea/phenomenal](https://github.com/openalea/phenomenal) | 3D reconstruction, plant architecture, growth tracking over time | mostly indoor / greenhouse research | Strong research repo for time-series structural tracking. More complex than this project likely needs initially. |
| RhizoVisionExplorer | [predictivephenomics/RhizoVisionExplorer](https://github.com/predictivephenomics/RhizoVisionExplorer) | Root image analysis | indoor / lab | Less relevant for top-down pot photos, but useful if root-crown or washed-root analysis ever matters. |
| LeafMachine2 | [Gene-Weaver/LeafMachine2](https://github.com/Gene-Weaver/LeafMachine2) | Leaf detection, segmentation, measurement | mostly specimen / close-up leaf imagery | Not gardening-specific, but its detection and segmentation approach is useful for leaf-focused pipelines. |
| Easy-Leaf-Area | [heaslon/Easy-Leaf-Area](https://github.com/heaslon/Easy-Leaf-Area) | Leaf area measurement and growth proxy tracking | indoor | Very useful for controlled photo capture if you want a quick leaf-area baseline without training a model first. |
| PlantShield AI | [hanessn1/PlantShield-AI](https://github.com/hanesn/PlantShield-AI) | Tomato leaf disease classification | indoor / close-up leaf diagnosis | Good disease-specific example repo with a more complete app stack than many notebook-only repos. |
| Tomato Leaf Disease Classification | [UmairPirzada/Tomato-leaf-disease-classification](https://github.com/UmairPirzada/Tomato-leaf-disease-classification) | Tomato disease classification | indoor / close-up leaf diagnosis | Useful as a lightweight disease-classification reference and dataset pointer. |

## Capability View

| Capability | Strongest repo candidates | Why they matter here |
|---|---|---|
| Plant segmentation from indoor images | [PlantCV](https://github.com/danforthcenter/plantcv), [Easy-Leaf-Area](https://github.com/heaslon/Easy-Leaf-Area) | Good fit for current indoor seedling and pot-stage tracking. |
| Plant segmentation from outdoor images | [PlantCV](https://github.com/danforthcenter/plantcv), [OpenWeedLocator](https://github.com/geezacoleman/OpenWeedLocator), [AgML](https://github.com/Project-AgML/AgML) | Useful when the project moves outside and backgrounds become noisier. |
| Pot identification | [PlantCV](https://github.com/danforthcenter/plantcv), [AgML](https://github.com/Project-AgML/AgML) | No obvious dedicated repo found; likely needs custom labeling and model training. |
| Plot / bed / row segmentation | [OpenWeedLocator](https://github.com/geezacoleman/OpenWeedLocator), [AgML](https://github.com/Project-AgML/AgML) | Better aligned with outdoor garden beds and later-season field-like imagery. |
| Growth tracking over time | [PlantCV](https://github.com/danforthcenter/plantcv), [Phenomenal](https://github.com/openalea/phenomenal), [Easy-Leaf-Area](https://github.com/heaslon/Easy-Leaf-Area) | Lets you turn repeated photos into coverage, area, or structural growth signals. |
| Disease detection | [PlantShield AI](https://github.com/hanesn/PlantShield-AI), [UmairPirzada/Tomato-leaf-disease-classification](https://github.com/UmairPirzada/Tomato-leaf-disease-classification), [AgML](https://github.com/Project-AgML/AgML) | Best for leaf close-ups and later disease triage workflows. |
| Fruit detection and counting | [tomatOD](https://github.com/up2metric/tomatOD), [AgML](https://github.com/Project-AgML/AgML) | Relevant once tomatoes set fruit and counting becomes a core outcome metric. |
| Weed / green-on-background detection | [OpenWeedLocator](https://github.com/geezacoleman/OpenWeedLocator), [AgML](https://github.com/Project-AgML/AgML) | Important for outdoor transition and separating crop vs non-crop regions. |

## AgML Datasets Worth Noting

AgML is especially useful because it aggregates agricultural datasets in one framework. The most relevant named datasets for this project are:

- `plant_seedlings_aarhus`: useful as a seedling-stage classification reference
- `fruit_detection_worldwide`: useful as a fruit detection training/evaluation reference
- `leaf_counting_denmark`: useful for count-oriented plant monitoring
- `sugarbeet_weed_segmentation`: useful for outdoor semantic segmentation patterns
- `carrot_weeds_germany`: useful for crop-vs-weed segmentation patterns

## Recommended Starting Stack For K's Tomato Trails

### Indoor now

1. Use [PlantCV](https://github.com/danforthcenter/plantcv) first for pot-region cropping, plant masking, coverage metrics, and connected-component counts.
2. Use [Easy-Leaf-Area](https://github.com/heaslon/Easy-Leaf-Area) as a simple benchmark for leaf-area tracking if photo framing can be standardized.
3. Build a custom pot detector using this repository's own labeled images, because pot identification looks like a project-specific gap rather than an existing package.

### Outdoor later

1. Keep PlantCV for baseline segmentation and measurements.
2. Pull in [AgML](https://github.com/Project-AgML/AgML) for outdoor segmentation and detection datasets.
3. Use [OpenWeedLocator](https://github.com/geezacoleman/OpenWeedLocator) as a practical reference for field-style green detection.
4. Add [tomatOD](https://github.com/up2metric/tomatOD) when fruit detection and counting becomes important.

## Commercial Products Using Camera Techniques

These are relevant references, but they do not provide open repos for the core product systems.

| Product | Official site | What it does |
|---|---|---|
| Gardyn | [mygardyn.com](https://mygardyn.com/) | Indoor hydroponic garden with camera-assisted monitoring and AI recommendations. |
| PictureThis | [picturethisai.com](https://www.picturethisai.com/) | Phone-camera plant identification and issue diagnosis. |
| PlantSnap | [plantsnap.com](https://plantsnap.com/) | Phone-camera plant identification. |
| Plantix | [plantix.net](https://plantix.net/en/) | Crop disease diagnosis from photos. |
| Cropler | [cropler.io](https://www.cropler.io/) | Remote camera monitoring for crops and fields. |
| Sigrow | [sigrow.com](https://sigrow.com/stomata-camera/) | Greenhouse-focused camera / sensing products for plant monitoring. |

## Bottom Line

For this repository, the most defensible path is:

1. start with PlantCV for segmentation and measurements
2. use AgML as the bridge to model training and public agricultural datasets
3. treat pot identification as a custom model problem
4. add tomatOD later for tomato fruit counting
5. borrow outdoor ideas from OpenWeedLocator when the trial moves outside
