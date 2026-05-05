# Third Party

This directory contains vendored or local tool packages that are not first-party ProxyTester application code.

```text
third_party/
  Deadpool-proxypool1.5/        Embedded proxy seed crawler used by collectors
  ui-ux-pro-max-skill-2.5.0/    Local UI/UX skill package archive
```

Application code should import through first-party wrappers such as `collectors.defaults`, not by hard-coding these paths in multiple places.
