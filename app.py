import json

import numpy as np

from scipy.sparse import coo_matrix
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap

from bokeh.plotting import figure, show
from bokeh.embed import json_item
from bokeh.resources import CDN
from bokeh.models import CustomJS, ColumnDataSource, Slider, Label, RangeSlider
from bokeh.models.layouts import Column

from models import FrameModel, AcquisitionModel, ClusterModel

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'your_database_uri' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Bootstrap(app)


def sparse_to_dense(data):
    data = np.array(data)

    if data.size == 0:
        return np.zeros((256, 256))

    x = data[:, 0]
    y = data[:, 1]
    values = data[:, 2]

    return coo_matrix((values, (x, y)), shape=(256, 256)).todense()


def generate_frame_plot(frame):
    sparse_data = json.loads(frame.frame_data)

    x = [t[0] for t in sparse_data]
    y = [t[1] for t in sparse_data]

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


def generate_counts_vs_time(acquisition_id):
    counts = list(db.session.query(FrameModel.counts).filter_by(acquisition_id=acquisition_id).all())

    plot = figure(x_range=(0, len(counts)), y_range=(0, max(counts)[0]),
                  width=500, height=250,
                  title="Counts Vs. Frames")
    plot.line(range(len(counts)), counts, line_color="black")
    return plot


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


@app.route('/')
def acquisition_page():
    acquisitions = db.session.query(AcquisitionModel).all()

    return render_template('acquisitions.html',
                           acquisitions=acquisitions)


@app.route('/acquisitions/<int:acquisition_id>')
def acquisition_view(acquisition_id):
    acquisition = db.session.query(AcquisitionModel).filter_by(id=acquisition_id).first()

    start = acquisition.frames[0]
    end = acquisition.frames[-1]

    return render_template('acquisition.html',
                           acq_start=start.id,
                           acq_end=end.id,
                           acq_count=len(acquisition.frames),
                           acquisition=acquisition,
                           resources=CDN.render())


@app.route('/acquisitions/<int:acquisition_id>/timeseries')
def aquisition_timeseries(acquisition_id):
    plot = generate_counts_vs_time(acquisition_id)
    return json.dumps(json_item(plot, "acquisition_timeseries"))


@app.route('/frame/<int:frame_id>')
def frame(frame_id):
    frame_obj = db.session.query(FrameModel).filter_by(id=frame_id).first()
    img = generate_frame_plot(frame_obj)

    return json.dumps(json_item(img, "frame"))


@app.route('/cluster/<int:cluster_id>/plot')
def cluster_plot(cluster_id):
    cluster = db.session.query(ClusterModel).filter_by(id=cluster_id).first()
    img = generate_cluster_plot(cluster)

    return json.dumps(json_item(img, "cluster"))


@app.route('/cluster/<int:cluster_id>')
def cluster(cluster_id):
    display_properties = ['bbox_area',
                          'convex_area',
                          'eccentricity',
                          'euler_number',
                          'extent',
                          'filled_area',
                          'frame_id',
                          'id',
                          'label',
                          'major_axis_length',
                          'max_intensity',
                          'min_intensity',
                          'minor_axis_length',
                          'orientation',
                          'perimeter',
                          'solidity',
                          'track_length']
    cluster = db.session.query(ClusterModel).filter_by(id=cluster_id).first()
    data_dict = cluster.to_dict()
    display_dict = {key: data_dict[key] for key in data_dict if key in display_properties}
    return json.dumps(display_dict)


@app.route('/cluster/search')
def search():
    pass


@app.route('/frame/<int:frame_id>/clusters')
def clusters(frame_id):
    frame_obj = db.session.query(FrameModel).filter_by(id=frame_id).first()

    cluster_ids = [cluster.id for cluster in frame_obj.clusters]
    return json.dumps(cluster_ids)


if __name__ == '__main__':
    app.run(debug=True)
