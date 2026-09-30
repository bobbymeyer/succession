/** A choice's buttons: over a picked-up card, or in the dock on a phone. */
export interface Offer {
  label: string;
  run(): void;
}

export function Offers({ offers }: { offers: Offer[] }) {
  return (
    <div className="offers" role="group" aria-label="Choose">
      {offers.map((o) => (
        <button key={o.label} type="button" className="offer" data-testid="offer" onClick={o.run}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
