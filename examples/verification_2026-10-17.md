# Claim verification run 2026-10-17T2021Z

Each claim from data/filing_notes/ was checked against the primary source named below.
Only CONFIRMED means the claim matches a primary source. PARTIAL means the part noted matches.
Everything else stays "unverified" in the digest.

| Status | Count |
|---|---|
| CONTRADICTED | 1 |
| CONFIRMED | 3 |
| PARTIAL | 4 |
| NOT_FOUND | 1 |
| PENDING | 4 |
| MANUAL | 4 |

## CONTRADICTED

### NTHI-form4-cmo-total (NTHI)
- Claim: CMO Thomas C. Chen bought 49,016 shares for about $210,000 since 2026-08-12
- From: data/filing_notes/NTHI_2026-09-17.md
- Check: sec_form4_purchases
- Result: Form 4 purchases 2026-08-12 to 2026-09-16: 59,814 shares, $249,998 total, average $4.1796. Lots: 2026-08-14: 33,787 sh @ $3.8477 (filed 2026-08-20, amending 2026-08-18); 2026-08-17: 2,472 sh @ $4.0445 (filed 2026-08-20, amending 2026-08-18); 2026-08-18: 12,757 sh @ $5.4870 (filed 2026-08-20); 2026-09-11: 5,556 sh @ $3.6000 (filed 2026-09-15); 2026-09-14: 5,242 sh @ $3.8150 (filed 2026-09-15). Differences: shares 59,814 vs claimed 49,016; total $249,998 vs claimed $210,000.
  - Form 4 filed 2026-09-15: https://www.sec.gov/Archives/edgar/data/1979414/000121390026100266/xslF345X06/marketforms-73995.xml
  - Form 4 filed 2026-08-20: https://www.sec.gov/Archives/edgar/data/1979414/000121390026092277/xslF345X06/marketforms-73819.xml
  - Form 4/A filed 2026-08-20: https://www.sec.gov/Archives/edgar/data/1979414/000121390026092276/xslF345X06/marketforms-73820.xml
  - Form 4 filed 2026-08-18 (replaced by a later 4/A, not counted): https://www.sec.gov/Archives/edgar/data/1979414/000121390026091231/xslF345X06/marketforms-72989.xml

## CONFIRMED

### NTHI-form4-ceo-0915 (NTHI)
- Claim: CEO Amir F. Heshmatpour bought 35,000 shares on 2026-09-15 at a weighted average of about $3.30
- From: data/filing_notes/NTHI_2026-09-17.md
- Check: sec_form4_purchases
- Result: Form 4 purchases 2026-09-15 to 2026-09-15: 35,000 shares, $115,395 total, average $3.2970. Lots: 2026-09-15: 35,000 sh @ $3.2970 (filed 2026-09-15).
  - Form 4 filed 2026-09-15: https://www.sec.gov/Archives/edgar/data/1979414/000121390026100269/xslF345X06/marketforms-73992.xml

### NTHI-form4-ceo-total (NTHI)
- Claim: CEO bought 111,000 shares for about $418,700 between the 2026-08-12 Phase 2a results and 2026-09-15
- From: data/filing_notes/NTHI_2026-09-17.md
- Check: sec_form4_purchases
- Result: Form 4 purchases 2026-08-12 to 2026-09-15: 111,000 shares, $418,854 total, average $3.7735. Lots: 2026-08-14: 12,000 sh @ $3.7883 (filed 2026-08-17); 2026-08-17: 3,000 sh @ $4.3733 (filed 2026-08-17); 2026-08-18: 9,000 sh @ $5.5400 (filed 2026-08-18); 2026-09-11: 37,000 sh @ $3.6654 (filed 2026-09-14); 2026-09-14: 15,000 sh @ $3.9600 (filed 2026-09-15); 2026-09-15: 35,000 sh @ $3.2970 (filed 2026-09-15).
  - Form 4 filed 2026-09-15: https://www.sec.gov/Archives/edgar/data/1979414/000121390026100269/xslF345X06/marketforms-73992.xml
  - Form 4 filed 2026-09-14: https://www.sec.gov/Archives/edgar/data/1979414/000121390026099422/xslF345X06/marketforms-73987.xml
  - Form 4 filed 2026-08-18: https://www.sec.gov/Archives/edgar/data/1979414/000121390026091150/xslF345X06/marketforms-73787.xml
  - Form 4 filed 2026-08-17: https://www.sec.gov/Archives/edgar/data/1979414/000121390026090894/xslF345X06/marketforms-73779.xml

### RARE-genglycos-fda-press (RARE)
- Claim: FDA granted accelerated approval to GENGLYCOS (Ultragenyx) for GSDIa on 2026-08-19, and the application received a Rare Pediatric Disease Priority Review Voucher
- From: data/filing_notes/RARE_2026-10-07.md
- Check: web_page_contains
- Result: Found ['For Immediate Release: August 19, 2026', 'accelerated approval for Genglycos', 'glycogen storage disease type Ia', 'The application for Genglycos received a Rare Pediatric Disease Priority Review Voucher', 'The FDA granted accelerated approval of Genglycos to Ultragenyx'] on the page.
  - FDA press announcement: https://www.fda.gov/news-events/press-announcements/fda-approves-first-therapy-patients-aged-8-years-and-older-glycogen-storage-disease-type-ia
  - ...er with Glycogen Storage Disease Type Ia Innovative gene therapy offers new option for children and adults with rare disease More Press Announcements For Immediate Release: August 19, 2026 The U.S. Food and Drug Administration today issued an accelerated approval for Genglycos (pariglasgene brecaparvovec-opnr) to reduce daily cornstarch...

## PARTIAL

### RARE-genglycos-approval (RARE)
- Claim: FDA approved GENGLYCOS (DTX401) for GSDIa on 2026-08-19 and awarded a priority review voucher
- From: data/filing_notes/RARE_2026-10-07.md
- Check: web_page_contains
- Result: Found ['GENGLYCOS', 'pariglasgene'] on the page. This confirms that FDA lists the product as approved; it does not confirm the approval date or the voucher.
  - FDA CBER, Approved Cellular and Gene Therapy Products: https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products
  - ..., Inc. ENCELTO (revakinagene taroretcel-lwey) Neurotech Pharmaceuticals, Inc. FAYUVI (rebisufligene etisparvovec-hopf) Ultragenyx Pharmaceutical Inc. GENGLYCOS (pariglasgene brecaparvovec-opnr) Ultragenyx Pharmaceutical Inc. GINTUIT (Allogeneic Cultured Keratinocytes and Fibroblasts in Bovine Collagen) Organ...

### RARE-fayuvi-approval (RARE)
- Claim: FDA approved FAYUVI (UX111) for MPS IIIA on 2026-09-17 and awarded a priority review voucher
- From: data/filing_notes/RARE_2026-10-14.md
- Check: web_page_contains
- Result: Found ['FAYUVI', 'rebisufligene'] on the page. This confirms that FDA lists the product as approved; it does not confirm the approval date or the voucher.
  - FDA CBER, Approved Cellular and Gene Therapy Products: https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products
  - ...icine ELEVIDYS (delandistrogene moxeparvovec-rokl) Sarapeta Therapeutics, Inc. ENCELTO (revakinagene taroretcel-lwey) Neurotech Pharmaceuticals, Inc. FAYUVI (rebisufligene etisparvovec-hopf) Ultragenyx Pharmaceutical Inc. GENGLYCOS (pariglasgene brecaparvovec-opnr) Ultragenyx Pharmaceutical Inc. GINTUIT (...

### SRRK-isembyld-approval (SRRK)
- Claim: FDA approved ISEMBYLD (apitegromab) for SMA in patients 2 and older on an SMN2-targeted treatment
- From: data/filing_notes/SRRK_2026-09-15.md
- Check: fda_drugsfda
- Result: BLA761463 original approval 2026-09-11. (Indication wording not checked; see the label on the application page.) This confirms that FDA approved ISEMBYLD and the approval date; it does not confirm the indication wording.
  - BLA761463 (SCHOLAR ROCK INC): https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=761463

### RARE-fayuvi-fda-press (RARE)
- Claim: FDA approved FAYUVI on 2026-09-17 for pediatric MPS IIIA, described by FDA as the first treatment; approval type and voucher as stated by the company
- From: data/filing_notes/RARE_2026-09-17.md
- Check: web_page_contains
- Result: Found ['For Immediate Release: September 17, 2026', 'today approved Fayuvi', 'the first treatment for pediatric patients with mucopolysaccharidosis type IIIA'] on the page. This confirms the approval date, the indication and FDA's 'first treatment' wording; it does not confirm the approval type ('standard full approval') or the Priority Review Voucher, which the FDA pages do not mention.
  - FDA press announcement: https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapy-pediatric-patients-sanfilippo-syndrome-type
  - ...Syndrome Type A Innovative gene therapy offers a new option for children with a rare, progressive neurodevelopmental disease More Press Announcements For Immediate Release: September 17, 2026 The U.S. Food and Drug Administration today approved Fayuvi (rebisufligene etisparvovec-hopf), the first treatment for pediatric patients with mucopo...

## NOT_FOUND

### NTHI-phase2a-protocol-results (NTHI)
- Claim: NEO100 Phase 2a results under the protocol-specified method (not published by the company)
- From: data/filing_notes/NTHI_2026-09-17.md
- Check: ctgov_results
- Result: NCT06047379 (RECRUITING): results not posted; NCT06357377 (RECRUITING): results not posted; NCT05023018 (RECRUITING): results not posted; NCT02704858 (ACTIVE_NOT_RECRUITING): results not posted. No registry results yet, so the protocol-method results are still unpublished.
  - https://clinicaltrials.gov/study/NCT06047379
  - https://clinicaltrials.gov/study/NCT06357377
  - https://clinicaltrials.gov/study/NCT05023018
  - https://clinicaltrials.gov/study/NCT02704858

## PENDING

### NTHI-redemption-amount (NTHI)
- Claim: Series A preferred redemption: 8-K says about $5,790,000 ($965/share); press release says $6.0 million stated value
- From: data/filing_notes/NTHI_2026-09-21.md
- Check: sec_filing_text
- Result: No 10-Q/10-K filed since 2026-10-01 yet. Rerun after the next one is filed.
  - https://data.sec.gov/submissions/CIK0001979414.json

### SRPT-regenxbio-payment (SRPT)
- Claim: Sarepta paid REGENXBIO the $39.0 million settlement within ten days of 2026-09-23
- From: data/filing_notes/SRPT_2026-09-23.md
- Check: sec_filing_text
- Result: No 10-Q/10-K filed since 2026-10-01 yet. Rerun after the next one is filed.
  - https://data.sec.gov/submissions/CIK0000873303.json

### QURE-bla-status (QURE)
- Claim: uniQure submitted the AMT-130 BLA on 36-month data; acceptance and FDA action date not disclosed
- From: data/filing_notes/QURE_2026-09-29.md
- Check: sec_filing_text
- Result: No 8-K/10-Q/10-K filed since 2026-09-30 yet. Rerun after the next one is filed.
  - https://data.sec.gov/submissions/CIK0001590560.json

### NBIX-roberts-employment-agreement (NBIX)
- Claim: New CMO Eiry W. Roberts: base salary $825,000, 60% target bonus, equity with target values of about $625,000 (options), $250,000 (RSUs) and $375,000 (performance RSUs); final Employment Agreement not yet filed
- From: data/filing_notes/NBIX_2026-09-28.md
- Check: sec_filing_text
- Result: No 10-Q/10-K filed since 2026-09-28 yet. Rerun after the next one is filed.
  - https://data.sec.gov/submissions/CIK0000914475.json

## MANUAL

### NTHI-abu-dhabi-ind (NTHI)
- Claim: Department of Health Abu Dhabi granted IND authorization for NEO100 (June 2026) and NEO212
- From: data/filing_notes/NTHI_2026-10-15.md
- Check: manual
- Result: Where to check: Department of Health Abu Dhabi news (https://www.doh.gov.ae/en/news; items load by JavaScript, so open it in a browser) and the DOH IRB Research Registry (https://www.doh.gov.ae/en/programs-initiatives/Test_code). On 2026-10-16 the registry page listed no study mentioning NeOnc, NEO100, NEO212 or glioma; the registry covers studies reviewed by the DOH ethics committee, not IND authorizations. Why not automated: No public API or searchable register found for DoH Abu Dhabi IND authorizations.

### NTHI-fda-meeting-1117 (NTHI)
- Claim: In-person End-of-Phase 1 Type B FDA meeting on NEO212 scheduled for 2026-11-17
- From: data/filing_notes/NTHI_2026-09-28.md
- Check: manual
- Result: Where to check: Next NTHI 8-K or 10-Q after 2026-11-17 in EDGAR (https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1979414&type=8-K&dateb=&owner=include&count=40); fetch_sec_8k.py will pick it up. Why not automated: FDA does not publish sponsor meeting schedules. Only the company can confirm it took place.

### SRRK-postmarketing-requirements (SRRK)
- Claim: FDA required a pregnancy safety study and asked for 15-day fracture alert reports
- From: data/filing_notes/SRRK_2026-09-15.md
- Check: manual
- Result: Where to check: ISEMBYLD approval letter on Drugs@FDA, BLA 761463 (https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=761463), under 'Approval Date(s) and History, Letters, Labels, Reviews'. Why not automated: Approval letters are PDFs; the requirement wording needs a human read.

### DYN-fda-designations (DYN)
- Claim: DYNE-101 has FDA Breakthrough Therapy, Orphan Drug and Fast Track designations
- From: data/filing_notes/DYN_2026-09-29.md
- Check: manual
- Result: Where to check: Orphan Drug: FDA Orphan Drug Designations database (https://www.accessdata.fda.gov/scripts/opdlisting/oopd/). Breakthrough and Fast Track are not published per product.. Why not automated: The orphan database is a search form without an API; Breakthrough and Fast Track grants are not public.

