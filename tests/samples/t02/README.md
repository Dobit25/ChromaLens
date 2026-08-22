# T02 real-backend fixtures

These five small, committed images are deterministic offline inputs for the
MediaPipe T02 integration gate. They are evidence that the real runtime returns
an aligned, non-empty mask and that the debug renderer visibly overlays it;
they are not an accuracy benchmark or a representative demographic dataset.

| File | Source record | Rights statement | SHA-256 |
| --- | --- | --- | --- |
| `astronaut.png` | [scikit-image 0.20 astronaut sample](https://scikit-image.org/docs/0.20.x/api/skimage.data.html#skimage.data.astronaut), Eileen Collins/NASA | Public-domain NASA image; redistributed by scikit-image | `88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5` |
| `cc0_woman.jpg` | [History Trust of South Australia via Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Woman_standing_in_a_garden_-_full_length_portrait(GN03697).jpg) | CC0 1.0 | `9659315a44a6d3eadf8814b314193aacc78033097aa4dee4da0fadbfcaec025d` |
| `loc_lincoln.jpg` | [Library of Congress record](https://www.loc.gov/pictures/item/2016817330/) | No known restrictions on publication; historical work in the public domain | `a305c6630a3ac49dc9fe2ebe9f218ba7bb91df715c2dd860d038a585e030c15f` |
| `loc_man.jpg` | [Library of Congress record](https://www.loc.gov/pictures/item/2006688036/) | No known restrictions on publication; historical work in the public domain | `50eb295eb7cf909350c67c74b3b306a1e7018261505c866f88f77b035ada0d94` |
| `nasa_shepard.jpg` | [NASA Alan Shepard portrait record via Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Alan_Shepard_in_1960.jpg) | Public-domain United States/NASA work; NASA insignia restrictions still apply | `3f8ef484565605683cfe5b4aec510c165afafbfe00477899faecfb521a097488` |

The committed JPEGs are the 960-pixel Wikimedia thumbnails or the Library of
Congress service copies linked by those records. The astronaut PNG is the
unchanged scikit-image 0.20 fixture. Do not replace a fixture without updating
its provenance, rights review, hash, and real-backend evidence.
