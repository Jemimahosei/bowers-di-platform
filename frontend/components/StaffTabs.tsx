import Link from "next/link";

/* Staff section pills from mockup 02 (Issues · Audiences · Times).
 * In the mockup these switch panels on one board; in the app they are
 * the existing routes — Issues = /campaigns, Audiences = /audiences,
 * Times = /dashboard (where Dr. Roberts' availability lives). */

const TABS = [
  { key: "issues", label: "Issues", href: "/campaigns" },
  { key: "audiences", label: "Audiences", href: "/audiences" },
  { key: "times", label: "Times", href: "/dashboard" },
] as const;

export type StaffTabKey = (typeof TABS)[number]["key"];

export default function StaffTabs({ active }: { active: StaffTabKey }) {
  return (
    <>
      <div className="od-tabs" role="group" aria-label="Staff sections">
        {TABS.map((t) => (
          <Link
            key={t.key}
            href={t.href}
            aria-current={t.key === active ? "page" : undefined}
          >
            {t.label}
          </Link>
        ))}
      </div>
      <p className="od-example-note">
        Counts come from the live platform data.
      </p>
    </>
  );
}
