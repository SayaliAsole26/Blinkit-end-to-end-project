---
name: Blinkit Review Analyzer
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#4c4733'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f1f1f1'
  outline: '#7d7761'
  outline-variant: '#cec6ad'
  surface-tint: '#6d5e00'
  primary: '#6d5e00'
  on-primary: '#ffffff'
  primary-container: '#ffe141'
  on-primary-container: '#736300'
  inverse-primary: '#e2c624'
  secondary: '#5f5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e2dfde'
  on-secondary-container: '#636262'
  tertiary: '#00696c'
  on-tertiary: '#ffffff'
  tertiary-container: '#0efaff'
  on-tertiary-container: '#006f72'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffe24d'
  primary-fixed-dim: '#e2c624'
  on-primary-fixed: '#211b00'
  on-primary-fixed-variant: '#524600'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1c1b1b'
  on-secondary-fixed-variant: '#474746'
  tertiary-fixed: '#2efaff'
  tertiary-fixed-dim: '#00dce1'
  on-tertiary-fixed: '#002021'
  on-tertiary-fixed-variant: '#004f51'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1440px
  gutter: 1.5rem
  margin-page: 2rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 2rem
---

## Brand & Style
The design system focuses on cognitive clarity and professional utility for B2B decision-makers. The brand personality is objective, analytical, and efficient, moving away from subjective sentiment to focus on structural insights. 

The visual style is **Corporate Modern** with a high-density information architecture. It utilizes a neutral foundation to allow the data to lead, while employing a distinctive warm yellow accent to highlight interactive paths and primary actions without the bias of traditional "success/failure" color coding. The interface prioritizes whitespace around complex data visualizations to reduce cognitive load.

## Colors
The palette is engineered for neutrality and functional signaling. 
- **Primary (#FFE141):** A warm yellow used strictly for branding and primary calls to action. It acts as a "focus" color rather than a value judgment.
- **Surface & Background:** A tiered grayscale system using #F5F5F5 for the base and #FFFFFF for elevated cards to create clear containment.
- **Confidence Signaling:** Instead of sentiment, color is used to represent data reliability. High confidence (#22C55E), Medium (#F59E0B), and Low (#9CA3AF) help users weigh the statistical significance of insights.
- **Avoidance of Red/Green Binary:** No green/red mapping is used for "good/bad" reviews. All data points should be treated as neutral funnel observations.

## Typography
This design system utilizes **Inter** for its exceptional legibility in data-heavy environments. 
- **Headlines:** Use tight letter-spacing and bold weights to provide strong visual anchors for dashboard sections.
- **Numerical Data:** Tabular figures should be enabled to ensure columns of numbers align perfectly in tables.
- **Labels:** Small, all-caps labels are used for axis titles and metadata to distinguish them clearly from interactive body text.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy for the desktop experience to maintain data density without overwhelming the user's field of vision.
- **Grid:** A 12-column grid with 24px (1.5rem) gutters.
- **Modules:** Content is grouped into logical modules. On desktop, sidebars are fixed (280px), while the main content area occupies the remaining span.
- **Mobile Reflow:** On mobile devices, the 12-column layout collapses into a single-column stack. Page margins reduce to 16px to maximize horizontal space for charts.

## Elevation & Depth
The design system uses **Tonal Layers** combined with **Ambient Shadows** to define hierarchy:
- **Level 0 (Background):** #F5F5F5. No shadow.
- **Level 1 (Cards):** #FFFFFF. Soft, diffused shadow (0px 4px 20px rgba(0,0,0,0.05)) with an 8px corner radius.
- **Level 2 (Dropdowns/Modals):** #FFFFFF. Sharp, focused shadow (0px 8px 30px rgba(0,0,0,0.12)) to indicate temporary interaction.
- **Outlines:** Use 1px solid #E5E5E5 for secondary boundaries within cards, such as table row separators or divider lines.

## Shapes
A hybrid shape language is applied to distinguish between structural containers and interactive triggers:
- **Containers:** Dashboard cards and input fields use `rounded-lg` (0.5rem) to maintain a professional, organized structure.
- **Interactions:** Buttons, tags, and badges utilize the **Pill** shape (999px) to provide a soft, tactile contrast against the rigid grid, signaling "clickability" clearly to the user.

## Components
- **Buttons:** Primary buttons are pill-shaped, filled with #FFE141, and use #1A1A1A text. Secondary buttons use a pill-shaped outline in #1A1A1A.
- **Badges:** Used for confidence levels. They are pill-shaped with a low-opacity background of the status color and a high-opacity text color (e.g., High Confidence: 10% opacity green background, 100% opacity green text).
- **Cards:** White surfaces with 0.5rem rounding and light ambient shadows. Headers within cards should be separated by a subtle 1px divider.
- **Input Fields:** 0.5rem rounded corners, 1px border (#E5E5E5). Focus state uses a 2px border of #FFE141.
- **Data Visualizations:** Use neutral blues and grays for the bulk of data. Use #FFE141 only to highlight the specific "Active Insight" or "Selected Node."
- **Funnel Stages:** Visualized as a series of connected pill-shaped segments, moving from "Cognitive Entry" to "Actionable Intent."