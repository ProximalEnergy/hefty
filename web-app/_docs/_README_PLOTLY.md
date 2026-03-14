# Plotly

## Custom plotly.js Bundle

The plotly.js package is very large when built with all plot types. To help reduce the size, a custom bundle can be built specifying only the required plot types. This is performed during build using the `build-plotly-custom.js` file.

**IMPORTANT** - Any trace types used in the application must be specified in the `"pnpm run custom-bundle -- --traces <trace,types,with,comma,separator>"` command.

If you are having trouble with adding new trace types, try uninstalling the `plotly.js` package, re-installing, and then building the custom bundle again.

```shell
pnpm remove plotly.js
pnpm add plotly.js
pnpm exec node build-plotly-custom.js
```

## References

- [Customizing the plotly.js bundle](https://github.com/plotly/react-plotly.js?tab=readme-ov-file#customizing-the-plotlyjs-bundle) (react-plotly.js)
