# Bowers D&I Platform — REAL Spec (from jem's Claude chat)

Source: `~/workspace/user/files/Claude-Application_process-20261026-1042.md`
(the Oct 21 export is a subset of the same conversation; line numbers below are
from the Oct 26 file). Read-only research, Nov 5, 2026. Nothing here was
invented — anything not in the chat is marked as such.

## 1. What the platform actually does

### 1.1 Whose tool it is, in jem's own words

jem is Program Manager & Data Analyst for the **Center for Belonging at
Cornell CIS Bowers** (hired Jun 12–Aug 14, 2026, 15 hrs/week; supervisor
Dr. LeeAnn Roberts, Director of the DEIB office). Her own description of the
job (chat L342):

> "i am also working as a program mananger for the center for belonging at
> cornell CIS bowers (my overall work is to organize diversoty and inclusion
> programs like Grace hopper, code Afrique and the tapia conference for
> underrepresented people in cornell, i helped designed the office space to be
> an inclusive hub and bring awarness to the community to utilize the
> resources we offer"

And the tool's purpose, again in her words (chat L2266):

> "working on building a platform/ tool for that, also buidling a tool that is
> able to reach all the minorities and people who will need help from us and
> get them to utlize [the resources]"

So the platform is **not a generic D&I directory**. It is the Center for
Belonging's working tool, and its core job is **reach**: find the
underrepresented students who need help and get them to actually use the
Center's resources. That is the design brief everything else hangs off.

### 1.2 The feature set, as stated in the chat

The fullest statement (chat L5896–5898, repeated L11555–11557):

> "surface resources to underrepresented students, track conference
> participation, automate outreach. You're the PM and you're building it.
> This is the Center for Belonging tool that hits both your PM and SWE resume
> simultaneously. And it has real institutional users from day one."

The Oct 2 comprehensive list (chat L11605) adds the concrete scope:

> "Surfaces resources to underrepresented students, tracks conference
> participation (Grace Hopper, Tapia, Code Afrique), automates outreach."

The resume inventory (chat L2554, repeated L11300/L11332) breaks it into
three tools:

- Minority student resource discovery tool
- Conference logistics tool (Grace Hopper, Tapia, Code Afrique)
- Building outreach platform — stack TBD from you

The system-design discussion (chat L6303, L6332) adds the scale
requirements:

> "real institutional scale. Multiple user roles (students, admins, faculty),
> event tracking, outreach automation, reporting. Forces real database schema
> design decisions."

System-design signals for this project (chat L6332): "Multi-role auth, schema
design, reporting pipeline".

The stack-recommendation answer (chat L2624–2631) adds one more explicit
feature:

> "What would make it even stronger: Add a data dashboard component with
> charts showing program participation trends. Now you've got React + Flask +
> PostgreSQL + data visualization in one project."

And the framing that governs all stack choices (chat L2624):

> "This is a real internal tool with real users — that context should drive
> the stack choice, not impressiveness."

That is what "real users > impressive stack" means in context: the tool is
judged by whether the Center's staff and students actually use it, not by
how impressive the tech looks. A working tool with real users beats a
flashier stack with none.

### 1.3 Users

From the chat, three roles (L6303): **students, admins, faculty**.

- **Students** (underrepresented students in CIS, esp. CS/IS): discover
  resources, see conferences and programs, get reached by outreach.
- **Admins / Center staff** (jem as Program Manager & Data Analyst):
  manage resources, log outreach, track conference participation, run
  reporting.
- **Faculty**: named as a role in the chat but no specific faculty workflow
  is ever described — open question (see §6).

### 1.4 Scale numbers from the chat (her resume bullets)

- **100+ students** served across the 3 flagship initiatives (L476, L615)
- **3 flagship initiatives**: Grace Hopper, Tapia, Code Afrique
- **2 academic departments**: Computer Science & Information Science (L476)
- **100+ stakeholders** across faculty, students, staff (L476)
- **40% increase** in student utilization of center resources through
  redesign of physical and operational workflows (L476, L4380, L5049)
- Budget: **CONFLICT** — L476 says "$2,000 program budget"; L4380 and
  L5049 say "$4,000 program budget". Unresolved; do not put either number
  on the platform until jem confirms.

### 1.5 Stack (settled by the chat)

Final lists (L11839, L11885, L12189, L18175) all agree:

**Next.js + TypeScript + FastAPI + PostgreSQL**

Earlier variants in the same chat (React + Flask + PostgreSQL at L11605;
FastAPI + PostgreSQL + React/TypeScript at L5896) were superseded by the
final lists. Deploy target named in the chat: **Railway** (L6226, L6241:
"Bowers Platform | ✅ FastAPI + PostgreSQL | ✅ React + TS | ❌ | ✅
Railway"). The current build uses docker-compose locally and has never been
deployed anywhere.

The chat also requires, for every project (L6303–6340):

- A system architecture diagram (boxes and arrows — client, server, DB,
  cache, external services)
- An `ARCHITECTURE.md` explaining what each component does, why it was
  chosen, and how it would scale
- A README section called "Design Decisions"

None of these exist in the current build.

## 2. Real content inventory

### 2.1 Verified real items (chat + web-verified Nov 5, 2026)

**Conferences / flagship programs — the three the chat names:**

| Program | Verified facts | Status / note |
|---|---|---|
| Grace Hopper Celebration | AnitaB.org; world's largest gathering of women in tech | **CANCELLED for 2026** — AnitaB.org cancelled GHC 2026 on Oct 13, 2026 (~2 weeks before its Oct 27–30 Anaheim dates) for funding shortfall. GHC India is still on Jan 20–22, 2027, Bangalore. The chat (Sep 2026) treats it as a live flagship; do NOT list GHC 2026 as an upcoming conference. Track it as a past/cancelled program, or list GHC India 2027. |
| Tapia — CMD-IT/ACM Richard Tapia Celebration of Diversity in Computing | Sep 16–18, 2026, Hyatt Regency Atlanta. Theme: "Shaping the Future of Computing: Empowering Inclusion, Innovation, and Impact." Tapia 2027 details coming soon (tapiaconference.cmd-it.org). | Real, happened Sep 2026. In the platform it belongs under past participation, with 2027 as the next cycle. |
| Code Afrique | Cornell Bowers CIS + Academic City University, Accra, Ghana. 2026 Summer Programme Aug 10–13, 2026 (4 days), 146 high school students from 13 Ghanaian high schools; Python, AI, data science, hackathon; mentors from Cornell, Meta, LinkedIn, IEEE. Originally "Ghana Hacks". Verified via diversity.cis.cornell.edu and acity.edu.gh. | Real, happened Aug 2026. jem co-facilitated with Dr. LeeAnn Roberts; her resume says 3-day delivery at Academic City University (chat L4066/L4140) — web sources say 4 days (Aug 10–13). Small conflict; use the web-verified 4 days unless jem corrects it. |

**The institution itself:**

- **Cornell Bowers CIS Office of Diversity, Equity, Inclusion, and
  Belonging (DEIB)** — "Belonging at Bowers", diversity.cis.cornell.edu.
  Director: **Dr. LeeAnn Roberts**. Associate Dean for Belonging:
  **Hakim Weatherspoon**. This is the office the platform belongs to; the
  platform should name it and link it, not present itself as a standalone
  generic product.

**Other real DEIB programs (web-verified, NOT named in the chat — candidates
for the resource list, need jem's confirmation before presenting as hers):**

- **CSMore** — summer program for rising sophomores (Jul 15–Aug 9), run by
  the DEIB office in Gates Hall; funded by the CS department, NSF, LinkedIn,
  Hopper-Dean Foundation. (bowers.cornell.edu)
- **Belonging at Bowers Awards** — annual awards celebrating faculty, staff,
  students, alumni, community leaders.
- **Impact Week (B@C 360)** — college-wide belonging week, Sep 28–Oct 4;
  committee lead Dr. LeeAnn Roberts.

**Related student orgs (from jem's campus involvement in the chat, L3019 —
NOT confirmed as platform content):** NSBE, ColorStack, Rewriting the Code,
Women in Computing at Cornell (WICC), URMC, ACSU, ISSA, Queery. These are
orgs she belongs to / that matter for recruiting; the chat never says they
belong in the platform. Do not add them as platform content without asking
her.

### 2.2 What is NOT in the chat (missing / unknown)

- **No named resources.** The chat never names a single resource (no
  tutoring program, no scholarship, no advising office, no specific link).
  The resource list is the platform's core feature and its content is
  entirely unwritten. jem (or the Center) must supply it.
- **No student names or individual records.** Only aggregate counts
  (100+ students). No per-student data exists anywhere in the chat.
- **No outreach copy.** "Automate outreach" is stated but no email
  template, audience rule, or send flow is ever described.
- **No faculty workflow.** Faculty are named as a role (L6303) with no
  described use.
- **No event list beyond the 3 conferences.** "Event tracking" is required
  but no Center events (info sessions, workshops, tabling) are named.
- **No reporting spec.** "Reporting" is required but no report format,
  audience, or metric is defined beyond participation-trend charts.

### 2.3 What the current build's seed actually is (all invented)

Every item in `backend/app/seed.py` is placeholder, per the file's own
header ("Nothing here refers to a real person or a real program — every name
is invented sample content"):

- **8 resources, all invented, all links `example.org`**: Peer Tutoring Hub,
  First-Generation Student Guide, Career Mentorship Network, Scholarship &
  Funding Database, Student Organization Directory, Graduate Student Support
  Circle, Transfer Student Welcome Kit, Undergraduate Research
  Opportunities Board.
- **6 outreach entries, all invented programs** (Fall Campus Outreach Fair,
  Intro to Computing Workshop, Community Mentorship Drive, New Student
  Welcome Week Outreach, Spring Resource Tabling, Alumni Mentorship Mixer)
  with invented contact counts (40–200).
- **5 conferences, all invented** (National Diversity in Computing
  Symposium, Student Leaders in Tech Conference, Undergraduate Computing
  Research Showcase, Women in Computing Leadership Forum, Accessibility in
  Tech Summit) with invented dates/locations/attendee counts. **None of the
  three real conferences appears.**

## 3. Design direction

### 3.1 What the chat says: nothing about visual design

The chat contains **no colors, no theme, no reference site, no visual
direction** for this platform. The only design language anywhere near Bowers
is about the physical office (L342: "i helped designed the office space to
be an inclusive hub"). No screenshot, no Figma, no "make it look like X".

**RESOLVED by jem Nov 5, 2026: design follows the existing Cornell Bowers
websites** (bowers.cornell.edu Belonging at Bowers pages). Verified from the
live site's own CSS (Nov 5, 2026): Cornell carnelian red **#B31B1B** is the
dominant brand color (109 uses), dark navy **#000056**, light background
**#F7F7F7**, grays #757575 / #B6B6B6 / #DEDEDE / #E6E6E6, near-black text
#2A2A2A, orange accent #F8981D, font **TT Commons Pro** (sans) with TT
Commons Pro Mono. Clean institutional Cornell look: white background,
carnelian headers and accents, dark text, gray borders. TT Commons Pro is a
licensed font, so the build should use a close system-sans fallback stack
(e.g. Inter / system sans) unless the font files are licensed. The
builder-invented dark-green palette is retired.

### 3.2 What the current build looks like (builder-invented, not from jem)

`frontend/app/globals.css`: warm off-white background `#f7f7f4`, white
cards `#ffffff`, dark green accent `#0e6b4f` / dark header `#123527`,
muted sage text `#5c6b62`, amber warnings `#9a5b00`, system font stack.
Clean, quiet, institutional-generic. Nothing in the chat supports or
contradicts this palette — it was chosen by the builder.

### 3.3 Candidate references (NOT from the chat — for jem to pick)

- **Cornell Bowers / DEIB branding**: the university brand is Cornell
  carnelian red; the DEIB site is diversity.cis.cornell.edu ("Belonging at
  Bowers"). A platform that belongs to that office should at minimum not
  clash with it. **To confirm against the DEIB site before adopting.**
- **SOUP's playful theme** (yellow `#FFE4A3`, orange `#DC600B`, blue
  `#2596be`, monospace): a student club site. Wrong register for an
  institutional tool used by staff and faculty — do not copy it without
  jem explicitly choosing it.
- **Tone the chat does support**: "inclusive hub", welcoming, belonging,
  "you belong here" (the DEIB site's own words). Whatever palette is chosen,
  the tone should read warm and accessible, not corporate-cold.

## 4. Gap analysis: current build vs the real spec

| Part of current build | Verdict | Evidence |
|---|---|---|
| Stack (Next.js 15 + TS + FastAPI + Postgres, docker-compose) | **KEEP** | Matches the chat's final spec exactly (L11839/L12189/L18175). Deploy target should become Railway per the chat; docker-compose stays for local dev. |
| Home page (stat cards + 3 section links) | **KEEP structure, REPLACE numbers' meaning** | Stat cards are fine, but they count invented seed data. Once real content lands, the stats should reflect real participation (e.g. students reached across the 3 programs). |
| Resource discovery (search + category/audience filters) | **KEEP structure, REPLACE all content** | The feature matches the chat (surface resources to underrepresented students). All 8 seeded resources are invented with `example.org` links — every one must be replaced with real Center resources supplied by jem. Categories/audiences are builder-invented; jem should confirm or replace them. |
| Outreach tracking (log + totals + by-program breakdown) | **KEEP as a start, REBUILD toward the real feature** | The chat requires **automated outreach** (sending outreach emails) and reaching students who need help. The build only logs aggregate entries after the fact — no students, no email, no targeting. Needs: a Student model, outreach campaigns/audiences, and email sending (or at minimum a defined manual-outreach workflow). |
| Conference dashboard (upcoming list, deadlines, attendee counts, add form) | **KEEP structure, REPLACE content + ADD participation tracking** | Must list the real 3 (Tapia, Code Afrique, GHC status — see §2.1), not 5 invented ones. And the chat says "track conference **participation**" — the build only stores a headcount number per conference. Needs per-student participation records (who attended which conference) to be the feature the chat describes. |
| Data dashboard (participation-trend charts) | **MISSING — BUILD** | Explicitly required by the chat (L2624–2631: "charts showing program participation trends"). Nothing of the sort exists in the build. |
| Multi-role auth (students / admins / faculty) | **MISSING — BUILD** | Explicitly required (L6303, L6332: "Multi-role auth"). The build has **no auth at all** — anyone with the URL can read and add data. Must be added before any real use or public exposure. |
| Event tracking | **MISSING — BUILD** | Required alongside outreach automation and reporting (L6303). The build has conferences only; no general events model (info sessions, workshops, tabling). |
| Reporting | **MISSING — BUILD** | Required (L6303, L6332: "reporting pipeline"). The build has only the outreach stats endpoint (totals + by-program). No report views, no exports, no leadership reporting. |
| ARCHITECTURE.md + architecture diagram + README "Design Decisions" | **MISSING — BUILD** | Required by the chat for every project (L6303–6340). |
| Deploy | **REBUILD (deploy it)** | Chat names Railway. The build is local-only, never deployed, and `docker compose up` was never even run (Docker unavailable in the build VM). |

## 5. What "working prototype" must demonstrate (from the chat)

Against real Center data (or clearly-labeled stand-ins jem approves):

1. A student opens the platform and finds a real resource for their
   situation (search + filters over real Center resources).
2. An admin logs in (role-based) and sees participation across the 3 real
   programs, with trend charts — not invented headcounts.
3. An admin records outreach that actually reaches students (audience,
   message, sends or scheduled sends) — not just a log line after the fact.
4. Conference participation is per-student (who went to Tapia / Code
   Afrique), not a single attendee number.
5. A report an admin could show departmental leadership (the chat says jem
   "supported reporting to departmental leadership", L476).

## 6. Open questions only jem can answer

1. **Design reference**: RESOLVED Nov 5, 2026 — follow the existing Cornell
   Bowers websites (see §3.1). Carnelian #B31B1B, TT Commons Pro, clean
   institutional look. Dark-green palette retired.
2. **Real resources**: the resource list is the core feature and the chat
   names none. Which real Center resources go in, with real names, blurbs,
   and links? Who supplies/maintains the list?
3. **Real users and access**: who are the actual users — Center staff only,
   or all CIS students? How do they log in (Cornell NetID / SSO, email
   allowlist, open)? Who is the admin who approves accounts?
4. **Outreach automation, concretely**: does "automate outreach" mean the
   platform sends emails itself (which provider / whose account), or does it
   prepare targeted lists and drafts for staff to send? What triggers a
   message?
5. **Participation data**: RESOLVED Nov 5, 2026 — there is NO roster list.
   jem does not have an actual list; the 100+ number is real (people she
   has personally worked with across all her programs), not fabricated.
   Participation is tracked going forward only. No student names exist
   anywhere — do not invent any.
6. **Faculty role**: the chat names faculty as a user role but gives them no
   workflow. What do faculty do in the platform, if anything?
7. **Grace Hopper**: GHC 2026 was cancelled. Should the platform list GHC
   India Jan 2027, keep GHC as a past program, or drop it until the next US
   cycle is announced?
8. **Budget number**: RESOLVED Nov 5, 2026 — use the biggest number:
   **$4,000**.
9. **Code Afrique duration**: RESOLVED Nov 5, 2026 — use the biggest
   number: **4 days** (Aug 10–13, 2026).
10. **Events**: which real Center events (info sessions, workshops, tabling)
    should the event tracker hold, beyond the 3 conferences?

## Source map (chat line numbers)

- jem's Center for Belonging role: L342, L472–479, L613–615
- Tool purpose ("reach all the minorities… get them to utilize"): L2266
- Feature statement: L5896–5898, L11555–11557, L11605
- Resume inventory (3 tools): L2552–2554, L11300, L11332
- Stack recommendation + data dashboard: L2624–2631
- "Real users drive the stack": L2624
- System design / multi-role / reporting: L6303, L6332
- Priority + deploy (Railway): L5915, L6226, L6241
- Final stack lists: L11839, L11885, L12189, L18175
- Scale numbers: L476, L615, L4063, L4380, L5049
- Code Afrique details: L4066, L4140, L4376, L5153, L5159; web-verified
  Nov 5, 2026 (diversity.cis.cornell.edu, acity.edu.gh)
- Tapia 2026: web-verified Nov 5, 2026 (tapiaconference.cmd-it.org; Sep
  16–18, 2026, Atlanta)
- GHC 2026 cancellation: web-verified Nov 5, 2026 (AnitaB.org, Oct 13,
  2026); GHC India Jan 20–22, 2027 still on
- DEIB office / CSMore / Impact Week / Awards: web-verified Nov 5, 2026
  (diversity.cis.cornell.edu, bowers.cornell.edu)

## 7. Recalibration answers (jem, Nov 5, 2026, in the Projects chat)

Before any design work, jem recalibrated the purpose and contents. Her
answers:

### 7.1 Real resources — from the two Bowers pages she linked

**Source pages:** https://bowers.cornell.edu/belonging-bowers and
https://bowers.cornell.edu/belonging-bowers/resources-and-support (read
Nov 5, 2026). These are the platform's real resource base; the invented
seed content must be replaced with these.

**Office services (resources-and-support):**
- Consultations — help planning DEIB programs/events/services; best
  practices; point of contact for DEIB concerns; submit a bias report on
  someone's behalf.
- Advising — one-on-one guidance: navigating campus resources, social
  connection strategies, mental health and wellness (culturally-responsive
  approaches), career development guidance.
- Funding / proposal support (faculty & staff) — thought partner on
  proposals and student sponsorship packages; letters of support; partner
  on broadening-participation proposals (CS, IS, statistics, data science).
- Contact: deib-office@bowers.cornell.edu.

**Community resources (linked out from resources-and-support):**
Anti-racism / Antisemitism / Islamophobia resources; mental health and
wellbeing (mentalhealth.cornell.edu); bias reporting; accessibility and
disability resources; OIETIX (Title IX); LGBTQ+ resources; OADI; Belonging
& Support Services (Student & Campus Life); Student Disability Services;
Future Faculty teaching/mentoring; OISE (graduate development); Office of
Postdoctoral Studies; International Services (Office of Global Learning);
Colleague Network Groups (HR employee resource groups); Department of
Inclusion and Belonging (HR); Inclusive Excellence Network (staff); OFDD
(faculty development & diversity); CTI inclusive-teaching course; CTL
(startups/commercialization); Diversity Alumni Programs + Cornell Mosaic.

**Campus partners:** Student & Campus Life, CALS, Cornell Engineering,
Arts & Sciences, Cornell Tech, ILR, Einaudi Center, Einhorn Center,
Financial Aid, Spirituality and Meaning-Making, Cornell Police, University
Assemblies.

**Programs on the Belonging at Bowers page (in addition to the 3 flagship
conferences):** CSMore (summer program for rising sophomores); Belonging
at Bowers Awards (annual); Dinner with the Deans+ (undergrads, professionals,
doctoral students with college leadership); EngageLEAP (doctoral scholars in
computing); a weeklong immersive research workshop inspiring underrepresented
students toward graduate study; a two-year program advancing students'
careers in tech (research, entrepreneurship, experiential learning); alumni
connections / mentorship small groups. Tagline on the page: "You belong
here." — Hakim Weatherspoon, Associate Dean for Belonging.

### 7.2 New programs jem named (not on the Bowers pages yet)

- **Meta Days** — Meta came to campus with a bunch of employees for a
  couple of days: talks in classes, coffee chats, dinners, panels between
  students and Meta employees.
- **Cornell alumni dinner** — happened not long ago, with alumni from
  startups and big tech; jem's words for the venue: "the Baytech
  building" (recorded as she said it — do not rename without confirming).

### 7.3 The gap the platform fills: newsletter + outreach + access

jem's idea for increasing reach:
- A **newsletter** that takes in information about the target audience
  (minorities and the people the Center serves) from student organizations
  such as **URMC and Cornell NSBE** (jem said "Nesby" — NSBE, National
  Society of Black Engineers).
- It **sends emails** to those people and reaches them through Cornell
  platforms such as **CampusGroups**.
- The platform should have access to that audience information, and the
  people trying to reach the Center and get resources should be able to do
  that through it too.
- **Quick appointment / call booking**: a fast way to get an appointment or
  hop on a call. **Dr. Roberts is the person to talk to for further
  information or to book appointments with.**
- Overall goal restated: make the resources more accessible.

NOTE (flag, not a decision): access to student-org member lists and
CampusGroups data needs those orgs' permission — the platform cannot assume
it. How the newsletter audience is built (opt-in signup vs org rosters) is
still to be settled with jem and the orgs.

### 7.4 Numbers: use the biggest

- Budget **$4,000** (not $2,000). Code Afrique **4 days** (not 3).
  (Also resolved in §6 items 8–9.)

### 7.5 Design: consistent with the existing websites

See §3.1 — Cornell Bowers look (carnelian #B31B1B, TT Commons Pro). This
resolves the design pick: Cornell / DEIB branding.

### 7.6 Still open after recalibration

- Login method: who logs in and how (Cornell NetID/SSO, email allowlist,
  open)? Who approves accounts?
- Faculty workflow: named role, no described use.
- GHC handling: list GHC India Jan 2027, keep GHC as a past program, or
  drop it until the next US cycle?
- Newsletter mechanics: opt-in signup vs org rosters; who sends from which
  account; CampusGroups integration — what is actually available.
- Appointment booking: what times does Dr. Roberts offer, and through what
  (a form that emails the office, a calendar link, or something else)?
