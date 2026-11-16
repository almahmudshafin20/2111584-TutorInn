export default function HomeHeroIllustration() {
  return (
    <svg
      className="home-hero-illustration"
      viewBox="0 0 680 520"
      role="img"
      aria-labelledby="home-hero-title home-hero-description"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title id="home-hero-title">TutorInn learning workspace</title>
      <desc id="home-hero-description">A laptop showing a tutoring dashboard, surrounded by learning cards, books, a notebook and pencils.</desc>
      <defs>
        <linearGradient id="hero-device" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--illustration-surface-raised)" />
          <stop offset="1" stopColor="var(--illustration-highlight)" />
        </linearGradient>
        <linearGradient id="hero-book" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--illustration-surface-raised)" />
          <stop offset="1" stopColor="var(--illustration-highlight)" />
        </linearGradient>
      </defs>

      <ellipse cx="345" cy="440" rx="292" ry="34" fill="var(--illustration-shadow)" opacity=".55" />
      <path d="M84 335c-26-89 35-184 119-205 71-18 104 20 169-16 77-43 175-27 220 41 47 70 22 157-37 201-75 56-393 65-471-21Z" fill="var(--illustration-highlight)" opacity=".75" />

      {/* Floating learning cards */}
      <g transform="rotate(-8 150 135)">
        <rect x="48" y="88" width="178" height="92" rx="17" fill="var(--illustration-shadow)" opacity=".35" />
        <rect x="43" y="81" width="178" height="92" rx="17" fill="var(--illustration-surface)" stroke="var(--illustration-line)" strokeWidth="2" />
        <rect x="61" y="101" width="38" height="38" rx="11" fill="var(--illustration-highlight)" />
        <path d="M70 130v-12m10 12v-20m10 20v-15" stroke="var(--illustration-accent)" strokeWidth="5" strokeLinecap="round" />
        <path d="M112 108h86M112 126h66M112 144h52" stroke="var(--illustration-ink)" strokeOpacity=".72" strokeWidth="6" strokeLinecap="round" />
      </g>
      <g transform="rotate(6 510 105)">
        <rect x="437" y="54" width="174" height="91" rx="17" fill="var(--illustration-shadow)" opacity=".3" />
        <rect x="432" y="48" width="174" height="91" rx="17" fill="var(--illustration-surface)" stroke="var(--illustration-line)" strokeWidth="2" />
        <rect x="450" y="66" width="34" height="34" rx="10" fill="var(--illustration-highlight)" />
        <path d="m459 83 7 7 13-16" fill="none" stroke="var(--illustration-accent)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M497 75h87M497 94h67M497 113h51" stroke="var(--illustration-ink)" strokeOpacity=".68" strokeWidth="6" strokeLinecap="round" />
      </g>

      {/* Laptop screen */}
      <g>
        <path d="M177 165q2-18 21-18h289q19 0 21 18l25 219H151l26-219Z" fill="var(--illustration-shadow)" opacity=".42" />
        <path d="M184 159q2-17 20-17h284q18 0 20 17l24 214H159l25-214Z" fill="url(#hero-device)" stroke="var(--illustration-ink)" strokeOpacity=".72" strokeWidth="8" />
        <rect x="190" y="165" width="302" height="191" rx="7" fill="var(--illustration-surface)" />
        <rect x="208" y="181" width="125" height="17" rx="8" fill="var(--illustration-highlight)" />
        <circle cx="216" cy="189" r="4" fill="var(--illustration-accent)" />
        <path d="M228 189h91" stroke="var(--illustration-accent)" strokeWidth="5" strokeLinecap="round" />
        <rect x="208" y="211" width="70" height="120" rx="9" fill="var(--illustration-highlight)" />
        <rect x="219" y="223" width="48" height="8" rx="4" fill="var(--illustration-accent)" />
        <rect x="219" y="240" width="39" height="6" rx="3" fill="var(--illustration-muted)" opacity=".7" />
        <rect x="219" y="254" width="44" height="6" rx="3" fill="var(--illustration-muted)" opacity=".7" />
        <rect x="219" y="280" width="48" height="36" rx="7" fill="var(--illustration-surface-raised)" stroke="var(--illustration-line)" />
        <path d="M229 305v-10m10 10v-18m10 18v-13" stroke="var(--illustration-accent)" strokeWidth="5" strokeLinecap="round" />

        <rect x="290" y="211" width="89" height="54" rx="9" fill="var(--illustration-highlight)" />
        <rect x="301" y="222" width="29" height="29" rx="8" fill="var(--illustration-accent)" opacity=".88" />
        <path d="M309 229h13m-13 7h13m-13 7h8" stroke="var(--illustration-surface)" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M340 226h28M340 239h22M340 251h16" stroke="var(--illustration-ink)" strokeOpacity=".7" strokeWidth="4" strokeLinecap="round" />

        <rect x="389" y="211" width="88" height="54" rx="9" fill="var(--illustration-surface-raised)" stroke="var(--illustration-line)" />
        <circle cx="411" cy="238" r="14" fill="var(--illustration-highlight)" />
        <path d="M404 238h14m-7-7v14" stroke="var(--illustration-accent)" strokeWidth="3" strokeLinecap="round" />
        <path d="M433 229h31M433 242h25" stroke="var(--illustration-ink)" strokeOpacity=".65" strokeWidth="4" strokeLinecap="round" />

        <rect x="290" y="278" width="187" height="53" rx="9" fill="var(--illustration-surface-raised)" stroke="var(--illustration-line)" />
        <path d="M304 293h103M304 307h148M304 320h79" stroke="var(--illustration-muted)" strokeOpacity=".7" strokeWidth="5" strokeLinecap="round" />
        <path d="M145 375h369l43 35q5 8-9 11H119q-13-3-7-11l33-35Z" fill="url(#hero-device)" stroke="var(--illustration-ink)" strokeOpacity=".55" strokeWidth="3" />
        <path d="M249 383h164l-15 11H264l-15-11Z" fill="var(--illustration-line)" />
        <path d="M175 397h330" stroke="var(--illustration-surface)" strokeWidth="3" strokeLinecap="round" opacity=".8" />
      </g>

      {/* Stacked books */}
      <g transform="rotate(-3 115 365)">
        <rect x="25" y="360" width="158" height="40" rx="8" fill="var(--illustration-shadow)" opacity=".35" />
        <rect x="20" y="348" width="164" height="42" rx="8" fill="var(--illustration-accent)" />
        <rect x="29" y="354" width="146" height="28" rx="5" fill="url(#hero-book)" />
        <path d="M42 363h112" stroke="var(--illustration-line)" strokeWidth="3" strokeLinecap="round" />
        <rect x="40" y="395" width="168" height="39" rx="8" fill="var(--illustration-shadow)" opacity=".28" />
        <rect x="34" y="384" width="174" height="42" rx="8" fill="var(--illustration-accent-strong)" />
        <rect x="44" y="391" width="154" height="28" rx="5" fill="var(--illustration-surface-raised)" />
        <path d="M58 405h115" stroke="var(--illustration-line)" strokeWidth="3" strokeLinecap="round" />
      </g>

      {/* Open book */}
      <g transform="rotate(2 343 451)">
        <path d="M204 411q55-22 126 13 62-34 125-12l-6 75q-61-19-120 14-67-35-129-13l4-77Z" fill="var(--illustration-shadow)" opacity=".35" />
        <path d="M201 405q58-23 130 13v70q-67-32-134-12l4-71Z" fill="var(--illustration-surface)" stroke="var(--illustration-line)" strokeWidth="2" />
        <path d="M331 418q65-36 129-13l-4 71q-65-20-125 12v-70Z" fill="var(--illustration-surface-raised)" stroke="var(--illustration-line)" strokeWidth="2" />
        <path d="M331 418v70" stroke="var(--illustration-accent-mid)" strokeWidth="3" />
        <path d="M219 425q43-12 88 9m-89 8q42-12 88 9m-88 8q42-12 88 9m43-34q42-21 85-9m-85 26q42-21 84-9m-84 26q42-21 83-9" fill="none" stroke="var(--illustration-muted)" strokeOpacity=".55" strokeWidth="3" strokeLinecap="round" />
      </g>

      {/* Notebook and pencil */}
      <g transform="rotate(-5 548 427)">
        <rect x="476" y="402" width="164" height="72" rx="9" fill="var(--illustration-shadow)" opacity=".32" />
        <rect x="471" y="394" width="164" height="72" rx="9" fill="var(--illustration-surface)" stroke="var(--illustration-line)" strokeWidth="2" />
        <path d="M487 411h129M487 426h129M487 441h91" stroke="var(--illustration-muted)" strokeOpacity=".5" strokeWidth="3" strokeLinecap="round" />
        <path d="m508 455 83-26 8 12-83 26-14 2 6-14Z" fill="var(--illustration-warm)" />
        <path d="m508 455-6 14 14-2" fill="var(--illustration-ink)" />
        <path d="m591 429 8-2 8 12-8 2Z" fill="var(--illustration-accent)" />
      </g>

      {/* Small graduation cap accent */}
      <g transform="translate(531 300) rotate(8)">
        <path d="m0 20 42-17 42 17-42 18L0 20Z" fill="var(--illustration-accent)" />
        <path d="M15 28v17q27 18 54 0V28L42 40 15 28Z" fill="var(--illustration-accent-strong)" />
        <path d="M84 20v30" stroke="var(--illustration-warm)" strokeWidth="4" strokeLinecap="round" />
        <circle cx="84" cy="53" r="5" fill="var(--illustration-warm)" />
      </g>
    </svg>
  )
}
