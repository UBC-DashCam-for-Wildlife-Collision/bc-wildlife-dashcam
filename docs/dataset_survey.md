# Dataset Survey - BC Wildlife Dashcam

Last updated: May 2026

## Caltech Camera Traps

Metadata file: caltech_images_20210113.json  
Total images: 243,100  
Total annotations: 245,118  

### Target Species Coverage

| Species | Annotations | Notes |
|---|---|---|
| deer | 12,196 | Good coverage |
| coyote | 16,601 | Good coverage |
| raccoon | 11,390 | Good coverage |
| mountain_lion | 145 | Severe underrepresentation |
| elk | 0 | Absent from dataset |
| moose | 0 | Absent from dataset |
| bear | 0 | Absent from dataset |

## iNaturalist - British Columbia

| Species | Observations |
|---|---|
| deer | 30,681 |
| coyote | 3,217 |
| raccoon | 4,470 |
| bear | 9,604 |
| moose | 4,396 |
| elk | 2,178 |
| mountain_lion | 332 |

## iNaturalist - Global (mountain lion only)

| Species | Observations |
|---|---|
| mountain_lion | 14,770 |

Reason for global pull: BC-only count of 332 is insufficient for fine-tuning. 
Global observations required for this class only.

## Combined Totals and Risk Assessment

| Species | Caltech | iNaturalist | Total | Risk |
|---|---|---|---|---|
| deer | 12,196 | 30,681 | 42,877 | None |
| coyote | 16,601 | 3,217 | 19,818 | None |
| raccoon | 11,390 | 4,470 | 15,860 | None |
| bear | 0 | 9,604 | 9,604 | Low |
| moose | 0 | 4,396 | 4,396 | Medium |
| elk | 0 | 2,178 | 2,178 | Medium |
| cougar | 145 | 14,770 | 14,915 | Resolved |

## Pull Strategy

| Class | Source | Strategy |
|---|---|---|
| deer | Caltech + iNaturalist BC | Cap at 4,000 total |
| coyote | Caltech + iNaturalist BC | Cap at 4,000 total |
| raccoon | Caltech + iNaturalist BC | Cap at 4,000 total |
| bear | iNaturalist BC | All available (~9,604) |
| moose | iNaturalist BC | All available (~4,396) |
| elk | iNaturalist BC | All available (~2,178) |
| cougar | Caltech + iNaturalist global | All available (~14,915) |

## Key Findings

1. Three of seven target species (elk, moose, bear) are entirely absent from 
   Caltech Camera Traps. iNaturalist is the sole source for these classes.
2. Cougar is the highest-risk class. BC-only sources yield 477 images total. 
   Global iNaturalist pull resolves this but introduces domain diversity outside BC.
3. Deer, coyote, and raccoon are over-represented. Training caps required to 
   prevent class imbalance from suppressing learning on rare classes.
4. Target training set per class: 2,000-4,000 images. Classes below this 
   threshold receive augmentation to compensate.

## Google Sheet

[Dataset Survey - BC Dashcam](<[PASTE YOUR SHEET URL HERE](https://docs.google.com/spreadsheets/d/1Y6eoyN-Xk9b4K5EFB5Z_KzXpMCz_iQKWs1BjLjqWQ9k/edit?gid=0#gid=0)>)
