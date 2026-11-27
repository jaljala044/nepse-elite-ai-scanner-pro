# NEPSE Elite AI — mobile foundation

Research-only Android/iOS Expo prototype. Use Node.js 22 and run the following from this directory:

```bash
npm install
npx expo install --check
npm run typecheck
npx expo export --platform android --output-dir dist
```

The `mobile-checks` GitHub Actions workflow performs the same dependency compatibility, TypeScript and Android JavaScript-bundle checks. It creates a lockfile from the pinned direct dependencies and uploads it as a short-retention CI artifact for review. The generated lockfile is not yet committed, so a stable repository-pinned transitive dependency graph remains outstanding. The CI bundle export is not a native Android APK/AAB build or device acceptance test.

Home, Scan, Portfolio and More are navigable placeholders. Device appearance controls light/dark mode. No live data, account credentials, holdings, recommendations, network requests or orders are enabled. Missing values are explicitly unavailable. Do not ship until dependency pinning, native/device validation, accessibility, authentication, shared API contracts, privacy and security acceptance pass. App identifiers are provisional.

Next: commit a reviewed lockfile, add native Android build/device smoke testing, then connect only reviewed read-only API contracts after backend privacy acceptance.
