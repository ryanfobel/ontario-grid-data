importScripts("https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js");

function sendPatch(patch, buffers, msg_id) {
  self.postMessage({
    type: 'patch',
    patch: patch,
    buffers: buffers
  })
}

async function startApplication() {
  console.log("Loading pyodide!");
  self.postMessage({type: 'status', msg: 'Loading pyodide'})
  self.pyodide = await loadPyodide();
  self.pyodide.globals.set("sendPatch", sendPatch);
  console.log("Loaded!");
  await self.pyodide.loadPackage("micropip");
  const env_spec = ['https://cdn.holoviz.org/panel/wheels/bokeh-3.4.1-py3-none-any.whl', 'https://cdn.holoviz.org/panel/1.4.3/dist/wheels/panel-1.4.3-py3-none-any.whl', 'pyodide-http==0.2.1', 'holoviews', 'hvplot', 'numpy', 'pandas', 'requests']
  for (const pkg of env_spec) {
    let pkg_name;
    if (pkg.endsWith('.whl')) {
      pkg_name = pkg.split('/').slice(-1)[0].split('-')[0]
    } else {
      pkg_name = pkg
    }
    self.postMessage({type: 'status', msg: `Installing ${pkg_name}`})
    try {
      await self.pyodide.runPythonAsync(`
        import micropip
        await micropip.install('${pkg}');
      `);
    } catch(e) {
      console.log(e)
      self.postMessage({
	type: 'status',
	msg: `Error while installing ${pkg_name}`
      });
    }
  }
  console.log("Packages loaded!");
  self.postMessage({type: 'status', msg: 'Executing code'})
  const code = `
  \nimport asyncio\n\nfrom panel.io.pyodide import init_doc, write_doc\n\ninit_doc()\n\nfrom panel import state as _pn__state\nfrom panel.io.handlers import CELL_DISPLAY as _CELL__DISPLAY, display, get_figure as _get__figure\n\n_pn__state._cell_outputs['d9d0722b-4d3d-475d-8daa-55567001c6c4'].append("""# **Ontario grid data dashboard**\n\n## Roadmap:\n\n### **v0.1**\n* [x] Automate build with github action (\`panel convert notebooks/index.ipynb --to pyodide-worker --out docs --pwa --title \\"Ontario grid data\\"\`)\n* [x] [Add icon](https://discourse.holoviz.org/t/how-to-change-favicon/4016/4)\n* [ ] [refresh data](https://discourse.holoviz.org/t/how-best-to-reload-dataset-shown-in-a-panel-dashboard/4430/6) (e.g., every 15min or with a button) without reloading app\n* [ ] [Compress/Partition](https://stackoverflow.com/questions/73551783/how-to-read-filtered-partitioned-parquet-files-efficiently-using-pandass-read-p)/cache data for memory/startup time efficiency\n\n### **v0.2**\n* [ ] Add version number, about, link to github in footer\n* [ ] Add logging/debug info\n\n### **v0.3**\n* [ ] Refactor to make dashboard/plots configurable via yaml config file\n* [ ] Add tests\n\n### **v0.4**\n* [ ] Download data as zipped csv\n* [ ] Add electricity and gas pricing data\n* [ ] Add local weather data\n* [ ] Update github readme with link to dashboard\n\n### **v0.5**\n* [ ] Load greenbutton gas and electricity data\n* [ ] backup/restore/share user data (with optional encryption keys) to local cache, google drive\n* [ ] Private devices\n\n## **v0.6**\n* [ ] Calculate co2, pricing (compare reate plans), calculate carbon tax + rebate\n* [ ] Fit caltrack models\n\n## **v0.7**\n* [ ] Add forecasting""")\n#%conda install -c conda-forge panel pandas numpy holoviews hvplot pyarrow arrow matplotlib python-dotenv\n\nimport datetime as dt\nimport io\nimport requests\n\nimport panel as pn\nimport pandas as pd\nimport numpy as np\nimport holoviews as hv\nimport hvplot.pandas\n\n\n# workaround for iphone\ndef _read_csv(url, *args, **kwargs):\n    response = requests.get(url)\n    return pd.read_csv(io.StringIO(response.content.decode('utf-8')), *args, **kwargs)\n\n# helper function for getting data\ndef get_series(**options):\n    df = _read_csv(options["url"], index_col=0, compression=None)\n    df.index = pd.to_datetime(df.index, utc=True).tz_convert(options["tz"])\n    df = df.sort_index(ascending=True)\n    return df[[options["column"]]].rename(columns={options["column"]: options["name"]})\n\n\n# helper function for getting data\ndef get_dataframe(**options):\n    df = _read_csv(options["url"], index_col=0, compression=None)\n    df.index = pd.to_datetime(df.index, utc=True).tz_convert(options["tz"])\n    df = df.sort_index(ascending=True)\n    return df\n\n\ndef utc_to_local(utc_dt):\n    return utc_dt.replace(tzinfo=dt.timezone.utc).astimezone(tz=None)\n\n\ndef local_to_utc(local_dt, tz):\n    return local_dt.tz_localize(tz=tz).astimezone(tz=dt.timezone.utc)\n\n\n# config options\nhvplot.extension("bokeh")\npn.config.theme = "dark"\nactive_tools = []\nbackend_opts={"plot.toolbar.autohide": True}\nheight=350\nwidth=750\nfontsize = {\n    'title': 24,\n    'labels': 18,\n    'xticks': 14,\n    'yticks': 14,\n    'legend': 14,\n}\noptions = dict(\n    url="https://raw.githubusercontent.com/ryanfobel/ontario-grid-data/main/data/clean/gridwatch.ca/hourly/summary.csv",\n    tz="America/Toronto",\n    column="",\n)\n\ndf = get_dataframe(**options)\n\nnow = df.index[-1]\nstart_time = now - dt.timedelta(days=90)\ndefault_range = (utc_to_local(now-dt.timedelta(days=7)), utc_to_local(now))\nrange_select = pn.widgets.DatetimeRangePicker(\n    value=default_range\n)\ndf = df[df.index > start_time]\nplot_options = dict(\n    value_label="MW",\n    legend="bottom",\n    title="Supply and demand",\n    height=height,\n    width=width,\n    stacked=False,    \n    grid=True,\n    fontsize=fontsize,\n    # ylim=(0, None),\n    # alpha=0.5,\n    # hover=False,\n)\ncolumns = {\n    "Power Generated (MW)": "supply",\n    "Ontario Demand (MW)": "demand",\n    "Imports (MW)": "imports",\n    "Exports (MW)": "exports",\n    "Net Import/Exports (MW)": "net (exports-imports)",\n}\nsuply_demand = df[columns.keys()].rename(columns=columns).hvplot.line(**plot_options).apply.opts(active_tools=active_tools, backend_opts=backend_opts, xlim=range_select, framewise=True)\n\nrxy = hv.streams.RangeX(source=suply_demand)\n\ndef update_widget(event):\n    new_dates = tuple([pd.Timestamp(i).to_pydatetime() for i in event.new])\n    if new_dates != range_select.value:\n        range_select.value = new_dates\nrxy.param.watch(update_widget, 'x_range')\n\n_pn__state._cell_outputs['2f3100be-51a7-4edc-b079-68061eb15650'].append((suply_demand))\nfor _cell__out in _CELL__DISPLAY:\n    _pn__state._cell_outputs['2f3100be-51a7-4edc-b079-68061eb15650'].append(_cell__out)\n_CELL__DISPLAY.clear()\n_fig__out = _get__figure()\nif _fig__out:\n    _pn__state._cell_outputs['2f3100be-51a7-4edc-b079-68061eb15650'].append(_fig__out)\n\nplot_options = dict(\n    value_label="MW",\n    legend="bottom",\n    title="Generation by source",\n    height=height,\n    width=width,\n    grid=True,\n    stacked=True,\n    ylim=(0, None),\n    alpha=0.4,\n    hover=False,\n    fontsize=fontsize,\n)\n\ncolumns = {x: x.replace(" (MW)", "") for x in df.columns if x.endswith(" (MW)") and (x[0]==x[0].lower())}\ngeneration = df[columns.keys()].rename(columns=columns).hvplot.area(**plot_options).apply.opts(active_tools=active_tools, backend_opts=backend_opts, xlim=range_select.value)\n_pn__state._cell_outputs['f34b8a86-2b00-44d0-b2b0-05a8189ad9e6'].append((generation))\nfor _cell__out in _CELL__DISPLAY:\n    _pn__state._cell_outputs['f34b8a86-2b00-44d0-b2b0-05a8189ad9e6'].append(_cell__out)\n_CELL__DISPLAY.clear()\n_fig__out = _get__figure()\nif _fig__out:\n    _pn__state._cell_outputs['f34b8a86-2b00-44d0-b2b0-05a8189ad9e6'].append(_fig__out)\n\nplot_options = dict(\n    value_label="%",\n    legend="bottom",\n    title="Relative generation by source",\n    height=height,\n    width=width,\n    grid=True,\n    stacked=True,\n    ylim=(0, 100),\n    alpha=0.4,\n    hover=False,\n    fontsize=fontsize,    \n)\n\ncolumns = {x: x.replace(" (%)", "") for x in df.columns if x.endswith(" (%)")}\ngeneration_pct = df[columns.keys()].rename(columns=columns).hvplot.area(**plot_options).apply.opts(active_tools=active_tools, backend_opts=backend_opts, xlim=range_select.value)\n_pn__state._cell_outputs['4269e893-a7f2-4230-b192-ffcd5c2a3228'].append((generation_pct))\nfor _cell__out in _CELL__DISPLAY:\n    _pn__state._cell_outputs['4269e893-a7f2-4230-b192-ffcd5c2a3228'].append(_cell__out)\n_CELL__DISPLAY.clear()\n_fig__out = _get__figure()\nif _fig__out:\n    _pn__state._cell_outputs['4269e893-a7f2-4230-b192-ffcd5c2a3228'].append(_fig__out)\n\noptions_gridwatch = dict(\n    name = "gridwatch",\n    url="https://raw.githubusercontent.com/ryanfobel/ontario-grid-data/main/data/clean/gridwatch.ca/hourly/summary.csv",\n    tz="America/Toronto",\n    column = "CO2e Intensity (g/kWh)"\n)\n\noptions_co2signal = dict(\n    name="co2signal",\n    url="https://raw.githubusercontent.com/ryanfobel/ontario-grid-data/main/data/clean/co2signal.com/CA-ON/hourly/output.csv",\n    column = "data.carbonIntensity",\n    tz="America/Toronto",\n)\n\ndf = get_series(**options_gridwatch).join(\n    get_series(**options_co2signal),\n    how="inner"\n)\n\nplot_options = dict(\n    value_label="g/kWh",\n    legend="bottom",\n    title="co2 emissions intensity",\n    height=height,\n    width=width,\n    grid=True,\n    ylim=(0, None),\n    fontsize=fontsize,    \n    # alpha=0.5,\n    # hover=False,\n)\ndf = df[df.index > start_time]\nco2_intensity = df.hvplot.line(**plot_options).apply.opts(active_tools=active_tools, backend_opts=backend_opts, xlim=range_select.value)\n_pn__state._cell_outputs['ecf16bd8-1397-4a56-b579-aedb23329d21'].append((co2_intensity))\nfor _cell__out in _CELL__DISPLAY:\n    _pn__state._cell_outputs['ecf16bd8-1397-4a56-b579-aedb23329d21'].append(_cell__out)\n_CELL__DISPLAY.clear()\n_fig__out = _get__figure()\nif _fig__out:\n    _pn__state._cell_outputs['ecf16bd8-1397-4a56-b579-aedb23329d21'].append(_fig__out)\n\nbutton_map = {\n    "Last 12 hours": dt.timedelta(hours=12),\n    "Last 24 hours": dt.timedelta(hours=24),\n    "Last 2 days": dt.timedelta(days=2),\n    "Last 7 days": dt.timedelta(days=7),\n    "Last 30 days": dt.timedelta(days=30),\n    "Last 90 days": dt.timedelta(days=90),\n    "Last 6 months": dt.timedelta(days=365./2),\n    "Last 1 year": dt.timedelta(days=365),\n}\n\nbuttons = [\n    pn.widgets.Button(name=name, button_type='light')\n    for name in button_map.keys()\n]\n\ndef b(event):\n    now = dt.datetime.now(dt.UTC)\n    delta = button_map[event.obj.name]\n    new_dates = tuple([utc_to_local(now-delta), utc_to_local(now)])\n    if new_dates != range_select.value:\n        range_select.value = new_dates\n\nfor button in buttons:\n    button.on_click(b)\n\ntemplate = pn.template.FastGridTemplate(\n    row_height=200,\n    theme_toggle=False,\n    theme="dark",\n    title=f"Ontario grid data (updated at { now.time().isoformat() })",\n    prevent_collision=True,\n    sidebar=[range_select, *buttons],\n    collapsed_sidebar=True,\n    logo="images/icon-vector.svg",\n)\ntemplate.main[0:2,0:6]=pn.panel(co2_intensity, sizing_mode='stretch_both')\ntemplate.main[0:2,6:12]=pn.panel(generation_pct, sizing_mode='stretch_both')\ntemplate.main[2:4,0:6]=pn.panel(suply_demand, sizing_mode='stretch_both')\ntemplate.main[2:4,6:12]=pn.panel(generation, sizing_mode='stretch_both')\n_pn__state._cell_outputs['7d36e6ce-ab13-4ef2-9bff-5aba739207c9'].append("""<img src=\\"images/icon-vector.svg\\" alt=\\"icon\\" width=\\"180\\"/>\n\nrenewable energy by Nawicon from <a href=\\"https://thenounproject.com/browse/icons/term/renewable-energy/\\" target=\\"_blank\\" title=\\"renewable energy Icons\\">Noun Project</a> (CC BY 3.0)""")\ntemplate.servable();\n\nawait write_doc()
  `

  try {
    const [docs_json, render_items, root_ids] = await self.pyodide.runPythonAsync(code)
    self.postMessage({
      type: 'render',
      docs_json: docs_json,
      render_items: render_items,
      root_ids: root_ids
    })
  } catch(e) {
    const traceback = `${e}`
    const tblines = traceback.split('\n')
    self.postMessage({
      type: 'status',
      msg: tblines[tblines.length-2]
    });
    throw e
  }
}

self.onmessage = async (event) => {
  const msg = event.data
  if (msg.type === 'rendered') {
    self.pyodide.runPythonAsync(`
    from panel.io.state import state
    from panel.io.pyodide import _link_docs_worker

    _link_docs_worker(state.curdoc, sendPatch, setter='js')
    `)
  } else if (msg.type === 'patch') {
    self.pyodide.globals.set('patch', msg.patch)
    self.pyodide.runPythonAsync(`
    from panel.io.pyodide import _convert_json_patch
    state.curdoc.apply_json_patch(_convert_json_patch(patch), setter='js')
    `)
    self.postMessage({type: 'idle'})
  } else if (msg.type === 'location') {
    self.pyodide.globals.set('location', msg.location)
    self.pyodide.runPythonAsync(`
    import json
    from panel.io.state import state
    from panel.util import edit_readonly
    if state.location:
        loc_data = json.loads(location)
        with edit_readonly(state.location):
            state.location.param.update({
                k: v for k, v in loc_data.items() if k in state.location.param
            })
    `)
  }
}

startApplication()