import bar from 'plotly.js/lib/bar'
import barpolar from 'plotly.js/lib/barpolar'
import box from 'plotly.js/lib/box'
import PlotlyCore from 'plotly.js/lib/core'
import heatmap from 'plotly.js/lib/heatmap'
import histogram from 'plotly.js/lib/histogram'
import icicle from 'plotly.js/lib/icicle'
import sunburst from 'plotly.js/lib/sunburst'
import waterfall from 'plotly.js/lib/waterfall'

PlotlyCore.register([
  bar,
  barpolar,
  box,
  heatmap,
  histogram,
  icicle,
  sunburst,
  waterfall,
])

export default PlotlyCore
