# Project Status Update - May 20, 2026
Prepared for: Dr. Thomas Johnson
Prepared by: Deepansh Sabharwal, Aditya Patel

## Current Status: Month 1, Week 2 - On Track

## Completed to Date

### Infrastructure
- GitHub organization and private repo live (ubco-dashcam/bc-wildlife-dashcam)
- Branch protection on main, both contributors active
- Interface contract documented and committed
- Meeting log maintained

### Dataset Pipeline (Deepansh)
- Full dataset survey completed across Caltech Camera Traps and iNaturalist BC
- Key finding: 3 of 7 target species absent from Caltech; iNaturalist is sole source for elk, moose, bear
- Key finding: cougar critically underrepresented in BC (477 total); global iNaturalist pull approved
- iNaturalist API pipeline built and validated
- MegaDetector v5a installed and validated (57% usable rate on raw iNaturalist images)
- 500 moose images downloaded and saved, elk download in progress

### Hardware and Electrical (Aditya)
- GPS interface spec documented
- Power budget calculated
- Hardware cart built, pending order after this meeting

## Hardware to Be Ordered Today
- Google Coral USB Accelerator
- SSD1306 128x64 OLED display
- Active piezo buzzer
- RGB LED bar
- Powered USB 3.0 hub
- SanDisk/Samsung High Endurance 128GB microSD
- Weatherproof enclosure + windshield mount
- USB-C 5V power adapter

## Remaining Month 1 Gates
- Complete species downloads for all 7 classes (this week)
- Run MegaDetector annotation pipeline on all downloaded images
- Hardware arrives and bench setup begins (next week)
- Camera calibration (OpenCV checkerboard)
- Unified dataset export to YOLOv8 format via Roboflow

## Timeline Assessment
On track for Month 1 deliverable: confirmed unified dataset and working hardware bench by end of May.

## Questions for Supervisor

1. **UBC ARC Access**
   We will require GPU compute for model fine-tuning in Month 2. Google Colab has 
   session time limits and is not suitable for overnight training runs. Could you 
   submit an ARC resource allocation request on our behalf this week? We need access 
   to a GPU node (V100 or A100) with sufficient storage quota for the dataset 
   (~50GB estimated). We want this in place before Month 2 begins.

2. **Highway 97 Road Test**
   Our Month 3 validation plan includes a test drive on Highway 97 in the Okanagan 
   corridor with the deployed system running in a vehicle. Does this require any 
   university ethics documentation, liability waivers, or departmental approval? 
   We want to identify and complete any required paperwork well in advance.

3. **Publication**
   We intend to target a conference paper submission based on this project's results. 
   Venues we are considering include IEEE ITSC and CRV (Canadian Conference on 
   Computer and Robot Vision). We would value your guidance on the most appropriate 
   venue and whether you would be willing to co-author.
