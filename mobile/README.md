# NEPSE Elite AI — mobile foundation

Research-only Android/iOS Expo prototype. Install Node.js 22 and run `npm install` in this directory, then `npx expo install --check`, `npm run typecheck` and `npm start`. SDK 54 is a starting baseline, not a verified current release recommendation. No lockfile or native device build has yet been generated.

Home, Scan, Portfolio and More are navigable placeholders. Device appearance controls light/dark mode. No live data, account credentials, holdings, recommendations, network requests or orders are enabled. Missing values are explicitly unavailable. Do not ship until dependency, device, accessibility, authentication and shared API acceptance checks pass. App identifiers are provisional.

Next: pin tested dependencies and lockfile, add mobile CI, connect only reviewed read-only API contracts, then implement authenticated portfolio access after backend privacy acceptance.
