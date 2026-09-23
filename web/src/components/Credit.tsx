// The line at the foot of every screen. target="_top", so from inside an
// iframe on someone's page it opens bobbymeyer.com in the whole window rather
// than squeezed into the frame; in a plain tab it is an ordinary link.
export function Credit() {
  return (
    <footer className="credit">
      <a href="https://bobbymeyer.com" target="_top">
        designed by bobbymeyer.
      </a>
    </footer>
  );
}
