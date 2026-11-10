"""Seed the database with the REAL Bowers content verified in
REAL-SPEC.md §7.1 (from the Bowers pages jem linked, read Nov 5, 2026).

Nothing here is invented. No testimonials, no invented names, events, or
resource descriptions. Community-resource descriptions only restate the
name/scope as given — no invented detail.

Seeded:
- Resources: Office services, Community resources, Campus partners.
- Conferences: Tapia 2026, Code Afrique 2026, GHC India, GHC 2026
  (cancelled — never upcoming), Tapia 2027 (tba).
- Events: the real Center programs named on the Belonging at Bowers page
  and by jem (CSMore, Awards, Dinner with the Deans+, EngageLEAP, Meta
  Days, Cornell alumni dinner, research workshop, two-year career program,
  alumni mentorship small groups, Impact Week). Dates are null unless a
  real date is known — never invented.
- One demo admin: admin@center.demo / demo1234 (demo only; see
  DEPLOY_NOTES.md).

NOT seeded (tracked going forward only): participation rows, newsletter
subscribers, appointments, outreach entries. No roster list exists.

Run standalone with:  python -m app.seed
(The API also seeds automatically on startup when the tables are empty.)
"""

from datetime import date

from sqlalchemy.orm import Session

from . import auth
from .database import SessionLocal
from .models import (
    Conference,
    Event,
    Resource,
    User,
)

HUB_LINK = "https://bowers.cornell.edu/belonging-bowers/resources-and-support"
BELONGING_LINK = "https://bowers.cornell.edu/belonging-bowers"

DEMO_ADMIN_EMAIL = "admin@center.demo"
DEMO_ADMIN_PASSWORD = "demo1234"


def _resources():
    rows = [
        # --- Office services (resources-and-support) ---
        Resource(
            title="Consultations",
            description="Help planning DEIB programs, events, and services; "
            "best practices; a point of contact for DEIB concerns; submit a "
            "bias report on someone's behalf.",
            category="Office services",
            audience="All students, faculty & staff",
            link=HUB_LINK,
        ),
        Resource(
            title="Advising",
            description="One-on-one guidance: navigating campus resources, "
            "social connection strategies, mental health and wellness with "
            "culturally-responsive approaches, and career development guidance.",
            category="Office services",
            audience="All students, faculty & staff",
            link=HUB_LINK,
        ),
        Resource(
            title="Funding and proposal support",
            description="For faculty and staff: a thought partner on proposals "
            "and student sponsorship packages, letters of support, and a "
            "partner on broadening-participation proposals in computer "
            "science, information science, statistics, and data science.",
            category="Office services",
            audience="All students, faculty & staff",
            link=HUB_LINK,
        ),
        Resource(
            title="Contact the DEIB office",
            description="Email deib-office@bowers.cornell.edu for further "
            "information or to book an appointment.",
            category="Office services",
            audience="All students, faculty & staff",
            link="mailto:deib-office@bowers.cornell.edu",
        ),
        # --- Community resources (linked out from resources-and-support).
        # Each description only restates its name/scope as given. All link
        # to the hub page that links them — no direct URLs are invented,
        # except the mental-health link, which is given. ---
        Resource(
            title="Anti-racism, antisemitism, and Islamophobia resources",
            description="Resources on anti-racism, antisemitism, and Islamophobia.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Mental health and wellbeing",
            description="Mental health and wellbeing resources.",
            category="Community resources",
            audience="All students",
            link="https://mentalhealth.cornell.edu",
        ),
        Resource(
            title="Bias reporting",
            description="Bias reporting resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Accessibility and disability resources",
            description="Accessibility and disability resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="OIETIX (Title IX)",
            description="OIETIX (Title IX) resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="LGBTQ+ resources",
            description="LGBTQ+ resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="OADI",
            description="OADI resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Belonging & Support Services (Student & Campus Life)",
            description="Belonging and support services from Student & Campus Life.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Student Disability Services",
            description="Student Disability Services.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Future Faculty teaching and mentoring",
            description="Future Faculty teaching and mentoring resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="OISE (graduate development)",
            description="OISE graduate development resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Office of Postdoctoral Studies",
            description="Office of Postdoctoral Studies resources.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="International Services (Office of Global Learning)",
            description="International Services, Office of Global Learning.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Colleague Network Groups (HR employee resource groups)",
            description="Colleague Network Groups — HR employee resource groups.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Department of Inclusion and Belonging (HR)",
            description="Department of Inclusion and Belonging (HR).",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Inclusive Excellence Network (staff)",
            description="Inclusive Excellence Network for staff.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="OFDD (faculty development and diversity)",
            description="OFDD — faculty development and diversity.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="CTI inclusive-teaching course",
            description="CTI inclusive-teaching course.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="CTL (startups and commercialization)",
            description="CTL — startups and commercialization.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        Resource(
            title="Diversity Alumni Programs and Cornell Mosaic",
            description="Diversity Alumni Programs and Cornell Mosaic.",
            category="Community resources",
            audience="All students",
            link=HUB_LINK,
        ),
        # --- Campus partners ---
        Resource(
            title="Campus partners",
            description="Student & Campus Life, CALS, Cornell Engineering, "
            "Arts & Sciences, Cornell Tech, ILR, Einaudi Center, Einhorn "
            "Center, Financial Aid, Spirituality and Meaning-Making, Cornell "
            "Police, University Assemblies.",
            category="Campus partners",
            audience="All students",
            link=BELONGING_LINK,
        ),
    ]
    return rows


def _conferences():
    return [
        Conference(
            name="Tapia 2026",
            date=date(2026, 9, 16),
            end_date=date(2026, 9, 18),
            location="Hyatt Regency Atlanta",
            status="past",
            description="CMD-IT/ACM Richard Tapia Celebration of Diversity "
            "in Computing. Theme: Shaping the Future of Computing: "
            "Empowering Inclusion, Innovation, and Impact.",
            link="https://tapiaconference.cmd-it.org",
            attendees=None,
        ),
        Conference(
            name="Code Afrique 2026",
            date=date(2026, 8, 10),
            end_date=date(2026, 8, 13),
            location="Academic City University, Accra, Ghana",
            status="past",
            description="Cornell Bowers CIS summer programme: 146 high school "
            "students from 13 Ghanaian high schools; Python, AI, data "
            "science, and a hackathon.",
            link="",
            attendees=None,
        ),
        Conference(
            name="GHC India",
            date=date(2027, 1, 20),
            end_date=date(2027, 1, 22),
            location="Bangalore",
            status="upcoming",
            description="Grace Hopper Celebration India.",
            link="",
            attendees=None,
        ),
        Conference(
            name="Grace Hopper Celebration 2026",
            date=date(2026, 10, 27),
            end_date=None,
            location="Anaheim",
            status="cancelled",
            description="Cancelled by AnitaB.org on Oct 13, 2026 due to a "
            "funding shortfall. Listed here only as a cancelled program — "
            "never as upcoming.",
            link="",
            attendees=None,
        ),
        Conference(
            name="Tapia 2027",
            date=None,
            end_date=None,
            location="TBD",
            status="tba",
            description="2027 details coming soon.",
            link="",
            attendees=None,
        ),
    ]


def _events():
    # Category "program" unless noted. Date null unless a real date is
    # known — never invented.
    return [
        Event(
            name="CSMore",
            description="Summer program for rising sophomores, held in Gates "
            "Hall (Jul 15–Aug 9).",
            date=None,
            status="active",
            category="program",
            location="Gates Hall",
        ),
        Event(
            name="Belonging at Bowers Awards",
            description="Annual awards celebrating faculty, staff, students, "
            "alumni, and community leaders.",
            date=None,
            status="active",
            category="program",
            location=None,
        ),
        Event(
            name="Dinner with the Deans+",
            description="Undergraduates, professionals, and doctoral students "
            "meet college leadership over dinner.",
            date=None,
            status="active",
            category="program",
            location=None,
        ),
        Event(
            name="EngageLEAP",
            description="Program for doctoral scholars in computing.",
            date=None,
            status="active",
            category="program",
            location=None,
        ),
        Event(
            name="Meta Days",
            description="Meta employees on campus for a couple of days: talks "
            "in classes, coffee chats, dinners, and panels with students.",
            date=None,
            status="active",
            category="program",
            location=None,
        ),
        Event(
            name="Cornell alumni dinner",
            description="Alumni from startups and big tech. Venue, in jem's "
            "words: the Baytech building.",
            date=None,
            status="active",
            category="program",
            location="Baytech building",
        ),
        Event(
            name="Weeklong immersive research workshop",
            description="A weeklong immersive research workshop inspiring "
            "underrepresented students toward graduate study.",
            date=None,
            status="active",
            category="workshop",
            location=None,
        ),
        Event(
            name="Two-year career program",
            description="A two-year program advancing students' careers in "
            "tech through research, entrepreneurship, and experiential learning.",
            date=None,
            status="active",
            category="program",
            location=None,
        ),
        Event(
            name="Alumni mentorship small groups",
            description="Alumni connections and mentorship in small groups.",
            date=None,
            status="active",
            category="program",
            location=None,
        ),
        Event(
            name="Impact Week (B@C 360)",
            description="College-wide belonging week, Sep 28–Oct 4.",
            date=None,
            status="active",
            category="program",
            location=None,
        ),
    ]


def seed(db: Session) -> dict:
    """Insert seed data only when the tables are empty. Returns counts."""
    counts = {"users": 0, "resources": 0, "conferences": 0, "events": 0}
    if db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first() is None:
        salt = auth.new_salt()
        db.add(
            User(
                name="Demo Admin",
                email=DEMO_ADMIN_EMAIL,
                password_hash=auth.hash_password(DEMO_ADMIN_PASSWORD, salt),
                salt=salt.hex(),
                role="admin",
            )
        )
        counts["users"] = 1
    if db.query(Resource).count() == 0:
        rows = _resources()
        db.add_all(rows)
        counts["resources"] = len(rows)
    if db.query(Conference).count() == 0:
        rows = _conferences()
        db.add_all(rows)
        counts["conferences"] = len(rows)
    if db.query(Event).count() == 0:
        rows = _events()
        db.add_all(rows)
        counts["events"] = len(rows)
    db.commit()
    return counts


def main() -> None:
    from .database import engine
    from .models import Base

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print(seed(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
