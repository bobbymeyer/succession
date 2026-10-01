import { bugReportUrl, buildName } from "../feedback";

// The line at the foot of every screen: the credit, which build this is, and
// where to report a problem. target="_top", so from inside an iframe on
// someone's page the credit opens bobbymeyer.com in the whole window rather
// than squeezed into the frame; in a plain tab it is an ordinary link.
export function Credit() {
  return (
    <footer className="credit">
      <a href="https://bobbymeyer.com" target="_top">
        designed by bobbymeyer.
      </a>
      <span className="build" data-testid="build">
        build {buildName()}
      </span>
      <a href={bugReportUrl()} target="_blank" rel="noopener">
        report a problem
      </a>
    </footer>
  );
}
