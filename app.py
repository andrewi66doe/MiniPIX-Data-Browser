
import json
import os
import logging

from flask import Flask
from flask import render_template, Blueprint, request, make_response

from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap

from bokeh.embed import json_item
from bokeh.resources import CDN

from werkzeug.utils import secure_filename
from config import DATABASE_URI
from models import FrameModel, AcquisitionModel, ClusterModel
from visualization import generate_frame_plot, generate_cluster_plot, generate_counts_plot

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Bootstrap(app)

log = logging.getLogger('pydrop')

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
    counts = list(db.session.query(FrameModel.counts).filter_by(acquisition_id=acquisition_id).all())

    plot = generate_counts_plot(counts)
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


@app.route('/upload_page', methods=['GET'])
def upload_page():
    return render_template('upload.html',
                           page_name='Main',
                           project_name="pydrop")


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']

    save_path = os.path.join('data', secure_filename(file.filename))
    current_chunk = int(request.form['dzchunkindex'])

    # If the file already exists it's ok if we are appending to it,
    # but not if it's new file that would overwrite the existing one
    if os.path.exists(save_path) and current_chunk == 0:
        # 400 and 500s will tell dropzone that an error occurred and show an error
        return make_response(('File already exists', 400))

    try:
        with open(save_path, 'ab') as f:
            f.seek(int(request.form['dzchunkbyteoffset']))
            f.write(file.stream.read())
    except OSError:
        # log.exception will include the traceback so we can see what's wrong
        log.exception('Could not write to file')
        return make_response(("Not sure why,"
                              " but we couldn't write the file to disk", 500))

    total_chunks = int(request.form['dztotalchunkcount'])

    if current_chunk + 1 == total_chunks:
        # This was the last chunk, the file should be complete and the size we expect
        if os.path.getsize(save_path) != int(request.form['dztotalfilesize']):
            log.error(f"File {file.filename} was completed, "
                      f"but has a size mismatch."
                      f"Was {os.path.getsize(save_path)} but we"
                      f" expected {request.form['dztotalfilesize']} ")
            return make_response(('Size mismatch', 500))
        else:
            log.info(f'File {file.filename} has been uploaded successfully')
    else:
        log.debug(f'Chunk {current_chunk + 1} of {total_chunks} '
                  f'for file {file.filename} complete')

    return make_response(("Chunk upload successful", 200))


if __name__ == '__main__':
    app.run(debug=True)


