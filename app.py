
import json

from bokeh.plotting import figure
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap

from bokeh.embed import json_item
from bokeh.resources import CDN

from config import DATABASE_URI
from models import FrameModel, AcquisitionModel, ClusterModel
from visualization import generate_frame_plot, generate_cluster_plot

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Bootstrap(app)


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


def generate_counts_vs_time(acquisition_id):
    counts = list(db.session.query(FrameModel.counts).filter_by(acquisition_id=acquisition_id).all())

    plot = figure(x_range=(0, len(counts)), y_range=(0, max(counts)[0]),
                  width=500, height=250,
                  title="Counts Vs. Frames")
    plot.line(range(len(counts)), counts, line_color="black")
    return plot