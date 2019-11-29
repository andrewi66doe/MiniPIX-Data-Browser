import json

import numpy as np
from bokeh.models import ColumnDataSource, CustomJS, Label, RangeSlider, Column
from bokeh.plotting import figure

from nputils import sparse_to_dense


def generate_frame_plot(frame):
    sparse_data = json.loads(frame.frame_data)

    img = np.array(sparse_to_dense(sparse_data))
    source = ColumnDataSource(data={'data': img.flatten()})
    plot = figure(x_range=(0, 256), y_range=(0, 256), width=750, height=750,
                  tools='hover,box_zoom,crosshair,reset,save',
                  tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")],
                  title="Frame {}".format(frame.id))
    im = plot.image(image=[img], x=0, y=0, dw=256, dh=256, palette="Viridis11")

    range_slider_callback = CustomJS(args=dict(source=source, im=im), code="""
                var image_source = im.data_source;
                var d = image_source.data['image'][0];
                var f = slider.value


                for (var i = 0; i < d.length; i++) {

                        if( source.data['data'][i] >= f[1]){
                            d[i] = f[1];
                        }else if(source.data['data'][i] <= f[0]){
                            d[i] = f[0];
                        } 
                        else{
                            d[i] = source.data['data'][i];
                        }

                }
                image_source.change.emit();
            """)

    for i, cluster in enumerate(frame.clusters):
        bbox = json.loads(cluster.bbox)
        label = Label(x=bbox[3], y=bbox[2], text=str(i + 1), text_color='red', text_font_size="8pt")
        plot.add_layout(label)
    slider = RangeSlider(start=1, end=np.max(img) + 2, step=1, title="View Window", value=(1, np.max(img)))
    slider.js_on_change('value', range_slider_callback)
    range_slider_callback.args['slider'] = slider
    plot.toolbar.logo = None
    layout = Column(slider, plot)

    return layout


def generate_cluster_plot(cluster):
    data = json.loads(cluster.intensity_image)
    bbox = json.loads(cluster.bbox)
    length = bbox[2] - bbox[0]
    width = bbox[3] - bbox[1]

    img = np.array(data)
    source = ColumnDataSource(data={'data': img.flatten()})

    plot = figure(match_aspect=True, width=350, height=350,
                  tools='hover,box_zoom,crosshair,reset,save',
                  tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")],
                  title="Cluster View")
    im = plot.image(image=[img], x=0, y=0, dw=width, dh=length, palette="Inferno11")

    range_slider_callback = CustomJS(args=dict(source=source, im=im), code="""
                var image_source = im.data_source;
                var d = image_source.data['image'][0];
                var f = slider.value


                for (var i = 0; i < d.length; i++) {

                        if( source.data['data'][i] >= f[1]){
                            d[i] = f[1];
                        }else if(source.data['data'][i] <= f[0]){
                            d[i] = f[0];
                        } 
                        else{
                            d[i] = source.data['data'][i];
                        }

                }
                image_source.change.emit();
            """)

    # plot.sizing_mode = "fixed"
    plot.toolbar.logo = None
    slider = RangeSlider(start=1, end=np.max(img) + 2, step=1, title="View Window", value=(1, np.max(img)))
    slider.js_on_change('value', range_slider_callback)
    range_slider_callback.args['slider'] = slider

    return Column(slider, plot)


