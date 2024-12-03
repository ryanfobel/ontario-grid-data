importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js");

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
  const env_spec = ['https://cdn.holoviz.org/panel/wheels/bokeh-3.6.2-py3-none-any.whl', 'https://cdn.holoviz.org/panel/1.5.4/dist/wheels/panel-1.5.4-py3-none-any.whl', 'pyodide-http==0.2.1', 'holoviews', 'hvplot', 'numpy', 'pandas', 'requests', 'setuptools_git_versioning']
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
  \nimport asyncio\n\nfrom panel.io.pyodide import init_doc, write_doc\n\ninit_doc()\n\nfrom panel import state as _pn__state\nfrom panel.io.handlers import CELL_DISPLAY as _CELL__DISPLAY, display, get_figure as _get__figure\n\n_pn__state._cell_outputs['d9d0722b-4d3d-475d-8daa-55567001c6c4'].append("""# **Ontario grid data dashboard**\n\nOnline dashboard available at https://ryanfobel.github.io/ontario-grid-data/\n\n## Roadmap:\n\n### **v0.1**\n* [x] Automate build with github action (\`panel convert notebooks/index.ipynb --to pyodide-worker --out docs --pwa --title \\"Ontario grid data\\"\`)\n* [x] [Add icon](https://discourse.holoviz.org/t/how-to-change-favicon/4016/4)\n* [x] [add git versioning](https://setuptools-git-versioning.readthedocs.io/en/stable/install.html)\n* [x] Add version number, about, link to github in footer\n\n### **v0.2**\n* [ ] [auto-refresh data](https://github.com/ryanfobel/ontario-grid-data/issues/44) (e.g., every 15min or with a button) without reloading app\n* [ ] Add logging/debug info\n* [ ] Fix apple icon and link\n\n### **v0.3**\n* [ ] [Compress/Partition](https://stackoverflow.com/questions/73551783/how-to-read-filtered-partitioned-parquet-files-efficiently-using-pandass-read-p)/cache data for memory/[profile](https://discourse.holoviz.org/t/loading-rendering-time-in-browser/2843/2) for startup time efficiency\n* [ ] Refactor to make dashboard/plots configurable via yaml config files\n\n### **v0.4**\n* [ ] Download data as zipped csv\n* [ ] Add electricity and gas pricing data\n* [ ] Add local weather data\n* [ ] Update github readme with link to dashboard\n\n### **v0.5**\n* [ ] Add tests\n* [ ] Load greenbutton gas and electricity data\n* [ ] backup/restore/share user data (with optional encryption keys) to local cache, google drive\n* [ ] Private devices\n* [ ] Fix resizing behaviour when datetime range changes (also when sidebar closes)\nI'm currently using a hidden dummy plot-hack to get resizing to work when the user changes the date range. [This](https://github.com/holoviz/panel/issues/1245) looks like maybe a better solution.\n\nAn earlier workaround was to replot each figure whenever the datetime range changes (this works, but performance suffers significantly):\n\n\`\`\`python\ndef on_range_changed(panels, event, plots):\n    for k, v in panels.items():\n        v[0] = pn.panel(plots[k], sizing_mode='stretch_both')\n\nrange_select.link(panels, callbacks={'value': ft.partial(on_range_changed, plots=plots)})\n\`\`\`\n\n## **v0.6**\n* [ ] Calculate co2, pricing (compare reate plans), calculate carbon tax + rebate\n* [ ] Fit [caltrack models](https://www.recurve.com/how-it-works/caltrack-billing-daily-methods)\n\n## **v0.7**\n* [ ] Add forecasting""")\n# imports, function defs\n\n#%conda install -c conda-forge panel pandas numpy holoviews hvplot pyarrow arrow matplotlib python-dotenv\n\nimport datetime as dt\nimport io\nimport requests\nimport functools as ft\nimport os\n\nimport panel as pn\nimport pandas as pd\nimport numpy as np\nimport holoviews as hv\nimport hvplot.pandas\n\n\ndef get_version():\n    try:\n        import setuptools_git_versioning\n\n        version = str(setuptools_git_versioning.get_version(root=".."))\n    except:\n        version = '0.1.dev99'\n    return 'v' + version\n\n\n# workaround for iphone\ndef _read_csv(url, *args, **kwargs):\n    response = requests.get(url)\n    return pd.read_csv(io.StringIO(response.content.decode('utf-8')), *args, **kwargs)\n\n\n# helper function for getting data\ndef get_series(**options):\n    df = _read_csv(options["url"], index_col=0, compression=None)\n    df.index = pd.to_datetime(df.index, utc=True).tz_convert(options["tz"])\n    df = df.sort_index(ascending=True)\n    return df[[options["column"]]].rename(columns={options["column"]: options["name"]})\n\n\n# helper function for getting data\ndef get_dataframe(**options):\n    df = _read_csv(options["url"], index_col=0, compression=None)\n    df.index = pd.to_datetime(df.index, utc=True).tz_convert(options["tz"])\n    df = df.sort_index(ascending=True)\n    return df\n\n\ndef utc_to_local(utc_dt):\n    return utc_dt.replace(tzinfo=dt.timezone.utc).astimezone(tz=None)\n\n\ndef local_to_utc(local_dt, tz):\n    return local_dt.tz_localize(tz=tz).astimezone(tz=dt.timezone.utc)\n\n\ndef load_gridwatch_data():\n    options = dict(\n        url="https://raw.githubusercontent.com/ryanfobel/ontario-grid-data/main/data/clean/gridwatch.ca/hourly/summary.csv",\n        tz="America/Toronto",\n        column="",\n    )\n    return get_dataframe(**options)\n\n\ndef plot_generation_by_source(data):\n    plot_options = dict(\n        value_label="MW",\n        legend="bottom",\n        title="Generation by source",\n        height=height,\n        width=width,\n        grid=True,\n        stacked=True,\n        ylim=(0, None),\n        alpha=0.4,\n        hover=False,\n        fontsize=fontsize,\n        xlim=default_range,\n    )\n    rename_columns = {x: x.replace(" (MW)", "") for x in data["gridwatch"].columns if x.endswith(" (MW)") and (x[0]==x[0].lower())}\n    return data["gridwatch"][rename_columns.keys()].rename(columns=rename_columns).hvplot.area(**plot_options)\n\n\ndef load_co2_intensity():\n    options_gridwatch = dict(\n        name = "gridwatch",\n        url="https://raw.githubusercontent.com/ryanfobel/ontario-grid-data/main/data/clean/gridwatch.ca/hourly/summary.csv",\n        tz="America/Toronto",\n        column = "CO2e Intensity (g/kWh)"\n    )\n    \n    options_co2signal = dict(\n        name="co2signal",\n        url="https://raw.githubusercontent.com/ryanfobel/ontario-grid-data/main/data/clean/co2signal.com/CA-ON/hourly/output.csv",\n        column = "data.carbonIntensity",\n        tz="America/Toronto",\n    )\n\n    return get_series(**options_gridwatch).join(\n        get_series(**options_co2signal),\n        how="inner"\n    )\n\n\ndef plot_co2_emissions_intensity(data):\n    plot_options = dict(\n        value_label="g/kWh",\n        legend="bottom",\n        title="co2 emissions intensity",\n        height=height,\n        width=width,\n        grid=True,\n        ylim=(0, None),\n        fontsize=fontsize,\n        xlim=default_range,\n        # alpha=0.5,\n        # hover=False,\n    )\n    return data["co2_intensity"].hvplot.line(**plot_options)\n\n\ndef plot_supply_demand(data):\n    plot_options = dict(\n        value_label="MW",\n        legend="bottom",\n        title="Supply and demand",\n        height=height,\n        width=width,\n        stacked=False,    \n        grid=True,\n        fontsize=fontsize,\n        xlim=default_range,\n        # ylim=(0, None),\n        # alpha=0.5,\n        # hover=False,\n    )\n    rename_columns = {\n        "Power Generated (MW)": "supply",\n        "Ontario Demand (MW)": "demand",\n        "Imports (MW)": "imports",\n        "Exports (MW)": "exports",\n        "Net Import/Exports (MW)": "net (exports-imports)",\n    }\n    return data["gridwatch"][rename_columns.keys()].rename(columns=rename_columns).hvplot.line(**plot_options)\n\n\ndef plot_generation_pct(data):\n    plot_options = dict(\n        value_label="%",\n        legend="bottom",\n        title="Relative generation by source",\n        height=height,\n        width=width,\n        grid=True,\n        stacked=True,\n        ylim=(0, 100),\n        alpha=0.4,\n        hover=False,\n        fontsize=fontsize,\n        xlim=default_range,\n    )\n    rename_columns = {x: x.replace(" (%)", "") for x in data["gridwatch"].columns if x.endswith(" (%)")}\n    return data["gridwatch"][rename_columns.keys()].rename(columns=rename_columns).hvplot.area(**plot_options)\n\n\ndef apply_plot_options(plots, range_select):\n    return {\n        k:(\n            v.apply.opts(active_tools=active_tools, backend_opts=backend_opts, xlim=range_select)\n            if k=='dummy'\n            else\n            v.apply.opts(active_tools=active_tools, backend_opts=backend_opts)\n        ) for k, v in plots.items()\n    }\n\n\ndef update_plots(data, range_select):\n    return apply_plot_options({\n        'generation_pct': plot_generation_pct(data),\n        'co2_intensity': plot_co2_emissions_intensity(data),\n        'supply_demand': plot_supply_demand(data),\n        'generation': plot_generation_by_source(data),\n    }, range_select)\n\n\ndef refresh_data():\n    global now, data, plots, panels, range_select\n    new_data = {\n        "gridwatch": load_gridwatch_data()\n    }\n    if new_data["gridwatch"].index[-1] > data["gridwatch"].index[-1]:\n        new_data["co2_intensity"] = load_co2_intensity()\n        data = new_data\n\n        # update range\n        now = data["gridwatch"].index[-1]\n        range_select.value=default_range = (utc_to_local(now-dt.timedelta(days=7)), utc_to_local(now))\n\n        plots = update_plots(new_data, range_select)\n        for k, v in panels.items():\n            v[0] = pn.panel(plots[k], sizing_mode='stretch_both')\n        debug.value=dt.datetime.now().isoformat()\n# config options\n\nhvplot.extension("bokeh")\ntheme = "dark"\npn.config.theme = theme\npn.extension()\n\n# disable linking of axes\n# hv.opts.defaults(\n#     hv.opts.Curve(axiswise=True, framewise=True, shared_axes=False),\n#     hv.opts.Area(axiswise=True, framewise=True, shared_axes=False),\n#     hv.opts.Scatter(axiswise=True, framewise=True, shared_axes=False),\n#     hv.opts.Image(axiswise=True, framewise=True, shared_axes=False),\n#     hv.opts.Histogram(axiswise=True, framewise=True, shared_axes=False)\n# )\n\nrefresh_period_minutes = 15\nactive_tools = []\nbackend_opts={"plot.toolbar.autohide": True}\nheight=350\nwidth=750\nfontsize = {\n    'title': 24,\n    'labels': 18,\n    'xticks': 14,\n    'yticks': 14,\n    'legend': 14,\n}\n\ndata = {}\nplots = {}\n# initialize dashboard\ndata["gridwatch"] = load_gridwatch_data()\nnow = data["gridwatch"].index[-1]\nstart_time = now - dt.timedelta(days=365)\ndefault_range = (utc_to_local(now-dt.timedelta(days=7)), utc_to_local(now))\nrange_select = pn.widgets.DatetimeRangePicker(\n    value=default_range\n)\n\ndata["gridwatch"] = data["gridwatch"][data["gridwatch"].index > start_time]\nplots["generation"] = plot_generation_by_source(data)\ndata["co2_intensity"] = load_co2_intensity()\ndata["co2_intensity"] = data["co2_intensity"][data["co2_intensity"].index > start_time]\nplots["co2_intensity"] = plot_co2_emissions_intensity(data)\nplots["supply_demand"] = plot_supply_demand(data)\nplots["generation_pct"] = plot_generation_pct(data)\nplots["dummy"] = plot_co2_emissions_intensity(data)\n\nbutton_map = {\n    "Last 12 hours": dt.timedelta(hours=12),\n    "Last 24 hours": dt.timedelta(hours=24),\n    "Last 2 days": dt.timedelta(days=2),\n    "Last 7 days": dt.timedelta(days=7),\n    "Last 30 days": dt.timedelta(days=30),\n    "Last 90 days": dt.timedelta(days=90),\n    "Last 6 months": dt.timedelta(days=365./2),\n    "Last 1 year": dt.timedelta(days=365),\n}\n\nplots = apply_plot_options(plots, range_select)\n\npanels = {\n    k: pn.Column(pn.panel(v, sizing_mode='stretch_both'))\n    for k, v in plots.items()\n}\n\nbuttons = [\n    pn.widgets.Button(name=name, button_type='light')\n    for name in button_map.keys()\n]\n\nsidebar_footer = pn.pane.Markdown(f"""\n{ get_version() }\n<a href="https://github.com/ryanfobel/ontario-grid-data/" target="_blank">About</a>\n""")\n\ntemplate = pn.template.FastGridTemplate(\n    row_height=200,\n    theme_toggle=False,\n    prevent_collision=True,\n    theme=theme,\n    title="Ontario grid data",\n    sidebar=[range_select, *buttons, sidebar_footer, pn.panel(plots["dummy"], visible=False)],\n    collapsed_sidebar=True,\n    logo="images/icon-vector.svg",\n)\n\ntemplate.main[0:2,0:6]=panels['co2_intensity']\ntemplate.main[0:2,6:12]=panels['generation_pct']\ntemplate.main[2:4,0:6]=panels['supply_demand']\ntemplate.main[2:4,6:12]=panels['generation']\n\n\ndef b(event):\n    global range_select\n    delta = button_map[event.obj.name]\n    new_dates = tuple([utc_to_local(now-delta), utc_to_local(now)])\n    if new_dates != range_select.value:\n        range_select.value = new_dates\n\nfor button in buttons:\n    button.on_click(b)\n\n# callback not working in pwa\n\nfor k, v in plots.items():\n    if k != "dummy":\n        display(v)\n_pn__state._cell_outputs['7d36e6ce-ab13-4ef2-9bff-5aba739207c9'].append("""<img src=\\"images/icon-vector.svg\\" alt=\\"icon\\" width=\\"180\\"/>\n\nrenewable energy by Nawicon from <a href=\\"https://thenounproject.com/browse/icons/term/renewable-energy/\\" target=\\"_blank\\" title=\\"renewable energy Icons\\">Noun Project</a> (CC BY 3.0)""")\ntemplate.servable();\n\nawait write_doc()
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