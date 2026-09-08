# Changelog

This changelog was compiled from `Reference - Feature Requests.docx`, a running notes document
kept by the stakeholders (RRHH, Comptabilitat, Projectes, and the digitalization team) to track
changes made to Justicier, open feature requests, and reported incidents. Related requests have
been merged into single entries; a few entries are vague or only loosely actionable in the source
document — they are kept as standalone points anyway, as requested.

## Delivered

- **Bulk (massive) load requests.** Charge/load requests can now be submitted in bulk, and the
  resulting uploads are routed into the requesting user's own folder.
- **Justification date handling fixed.** Requests now default the start date to the 1st of the
  month instead of the actual day work began — using the real start day used to break processing.
- **RLC/RNT merging.** RLC and RNT documents can be merged into a single justification; the merge
  was further tuned so arrears (endarreriments) only pull in the RLC periods that actually apply,
  instead of bundling in irrelevant documents, and was adapted to Projects' specific needs.
  **Known limitation carried over:** the merge still breaks when a justification has more than one
  endarreriment, and a payslip (nòmina) with two pages only has its first page merged.
- **Richer approval screen.** Approvals now show the requester's comment and whose payroll data is
  being requested; the approval notification message was also simplified to cut down on emails.
- **Request form enhancements.** Added an "Urgent" flag, and fields to indicate whether the IDC
  and/or a cost Excel are needed — reducing back-and-forth emails with Projects.
- **Document-count sanity check.** RRHH can now see a count of the documents present in a folder,
  making it easy to spot missing documentation.
- **Missing-document status flag.** A request is flagged green when the latest month's RLC/RNT is
  missing.
- **Cross-team folder conventions.** Users outside the Justicier team coordinated folder naming and
  a color-coded workflow with the project team.

## Known limitations (explicitly not done)

- Standardized handling of person "names" is not implemented yet.
- Template security hardening has not been applied yet.
- Input/output folder permissions can't be locked down, since these folders are created on the fly.
- The empty Excel template still needs to be adapted to match the fully-filled version.
- Note from the source doc: some items that ended up on the "suggestions" list did not actually
  originate from this team.

## In progress

- **Passport / NIE / DNI history.** Reported failure: a person who has held a passport, then a
  provisional NIE, then a final NIE/DNI needs one field per identifier today (a manual workaround
  by Mara). This matches ongoing work already in the codebase (`nif-historical` branch, e.g.
  "implemented nif history, but passport is not working properly, it is not selecting a present
  document") — worth checking against this request when that work lands.

## Backlog / requested features

**NAF/DNI list & filtering**
- Add filtering to the NAF/DNI Excel list (raised independently by RRHH, Comptabilitat, and via
  three separate incident reports).
- Lock the NAF_DNI file to read-only for everyone except RRHH — manual edits (including filters)
  break the automation that depends on it. Short term: read-only mode, access checked with the
  `dmp@iciq.es` admin account (Carles and Aleix keep admin rights since they're needed to
  administer the automation).
- Prevent blank Name/DNI/NAF fields; SharePoint's data model can't natively enforce "3 fields, at
  least 1 required," so add more warnings to the form/list in the meantime.
- Accept NAF numbers that contain a slash instead of rejecting them.

**Simplified request form using a "person" field**
- Replace searching the Excel/NAF/DNI lookup with a direct, email-based person selector. Long
  term, this also reduces/eliminates dependency on the NAF_DNI file, including read dependencies.
- Watch out for edge cases: a person with more than one email address, and IT deactivating a
  mailbox once someone has left (an address should stay valid for a set number of years).
- New form layout: Title, person name, start date, end date, with grouping options.

**Deadlines & scheduling**
- Define and enforce deadlines at every step of the process (request, document upload, correction
  turnaround), with committed turnaround times and named stakeholders for each stage.
- Proposed schedule: since RLC is paid a month later, request the justification on the 5th of the
  following month (e.g. justify June on August 5th).

**Error-report review workflow**
- Route the output error report to whoever supplied the original documentation (not the requester),
  let them fix/upload what's missing, then notify the actual requester once the correction is done.
- Define the error-handling procedure to follow between RRHH and Comptabilitat.
- Agree on where finished justifications are archived (SharePoint output) and avoid keeping
  duplicate copies of the same documentation.

**Approval workflow**
- Add comments to the approval step.
- Support two justification passes: a provisional one and a definitive one.

**Users & roles**
- Build user/role management: maintain a list of ICIQ users with their emails and assigned role
  (data feeder, supervisor, administrator).

**Document selection & naming**
- Allow requesting only the specific document type needed (e.g. just a contract or just a payslip)
  instead of the full bundle.
- Let users pick which contract/addenda applies and rename it, instead of always pulling every
  contract on file.
- Store scanned contracts and addenda.

**Load/upload form**
- Auto-complete the email field on the load form.
- Do not change the load Excel template — past changes to it have caused problems.

**Miscellaneous**
- Add a severance ("finiquito") ID field.
- Support project-related requests as a distinct request type.
- Add an in-app chat ("Xat Justicier").
- PowerAutomate integration for input/output.
- Link the documentation from the Justicier SharePoint's side menu so it's easy to find (this
  refers to the documentation itself, not the templates).
- Hand-signed finiquitos: previously tracked outside Justicier by request; per Mara this is no
  longer needed.
- A standalone/individual document request is considered out of scope for Justicier.
- "Video de duplicar" — a duplication-related video was mentioned with no further detail in the
  source notes; kept here as-is since it isn't otherwise actionable.

## Process objectives (organizational, not pure software features)

- Clearly mark the start of the justification process, its steps, and the parties involved, with
  committed deadlines for each task.
- Everyone involved should follow the same procedure.
- Define how incidents should be handled once raised.
- RRHH should organize itself to add any missing documentation at approval time.

## Department feedback (context captured during process analysis)

**Comptabilitat**
- Benefit: bank-proof documents no longer need to be manually searched for in ~100% of cases.
- Needs: documents uploaded on time; accurate RLC file naming.

**RRHH**
- Benefit: time spent searching for documentation has dropped significantly.
- Needs: documents uploaded on time with accurate names; ability to download the updated NAF Excel
  list; approve requests; verify documents against the report; store scanned contracts/addenda.
- Side effect: since Justicier is now faster, IDC and labor-cost reporting are also expected to
  move faster.

**Projectes**
- Benefit: justifications now arrive almost immediately instead of taking days, already grouped
  and organized, and benefit from RRHH's first-pass review via the report (though human error can
  still slip through).
- Needs: filling out the form takes more time than before; form mistakes must be avoided (and
  investigated when they happen); requesting even a single document still requires the full
  process.

## Known issues / incident log

| Date | Summary | Severity | Resolved | Category | Resolution |
|---|---|---|---|---|---|
| 2026-01-26 15:57 | Bulk-load instructions can't be downloaded | High | 2026-01-27 07:12 | Unknown Microsoft issue | Document was sent; no fix was needed — it started working for users again by morning on its own. Suggested follow-up: link the documentation in the Justicier SharePoint side menu. |
| 2026-01-23 10:02 | Requested a Jan–Dec 2025 justification with no RLC/RNT on file, yet it showed green — why? | Low | 2026-01-23 10:04 | Internal I/O logic | Justicier can't display data that doesn't exist; folder upkeep isn't its responsibility. Recommendation: wait until all documents are in place, or run two justifications — one to review, one for the Ministry submission. RRHH suggested emailing the latest RLC/RNT directly instead. Since justifications are now cheap to re-run, the flow can be: run once, tell RRHH what's missing, have them upload it, then re-run. |
| 2026-01-23 09:18 | Question about the NAF/DNI list filter | High | 2026-01-23 09:20 | UI question | Resolved — see the NAF_DNI lock-down and filtering items in the backlog above. |
| 2026-01-23 09:10 | Filter on the NAF/DNI list (ID 610) | High | 2026-01-23 09:12 | UI error | Filtering isn't possible yet; added to the backlog for the next version. Same root cause as the item above. |
| 2026-01-12 07:11 | Name/DNI/NAF left blank (ID 598) | High | 2026-01-12 07:15 (verbal) | UI error | Required fields can't be left blank; SharePoint's data model can't express "3 fields, at least 1 required." Likely improves with the "person" field; more form/list warnings added meanwhile. |
| 2026-01-12 | NAF containing a slash (ID 596) | High | 2026-01-12 | UI error | NAF with a slash is rejected; noted in the instructions. Requested fix: accept NAF values containing a slash. |
| 2026-01-08 07:11 | Bulk request where one of two records didn't come out | High | 2026-01-08 07:13 (tested, works); 07:33 (root cause: filtered Excel) | UI error | Caused by the same NAF/DNI filtering issue as above — a filtered list can't be used as input. |
