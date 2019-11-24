import time
import os
import re
import json

from itertools import islice
from numpy import array
from scipy.sparse import coo_matrix
from scipy.ndimage import label as nlabel
from scipy.ndimage import find_objects

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cv2 as cv
from sklearn.preprocessing import binarize

from skimage.measure import label, regionprops
from skimage.color import label2rgb

from mathutils import *
from models import *


class Acquisition:
    FRAME_WIDTH = 256
    FRAME_HEIGHT = 256

    def __init__(self, filename):
        self.filename = filename
        self.dscfilename = filename + '.dsc'
        self._frames = []

        if not (os.path.isfile(self.filename) and os.path.isfile(self.dscfilename)):
            raise Exception("Failed to find file {}".format(self.filename))

        self.dsc_file = open(self.dscfilename, 'r')
        self.acq = self.dsc_file.readline()
        self.load()

    def load(self):
        with open(self.filename, 'r') as pmffile:
            finished = False
            frames = 0

            while not finished:

                data = list(islice(pmffile, self.FRAME_HEIGHT))
                frame = []

                if not data:
                    finished = True
                for line in data:
                    frame.append([float(x) for x in line.split()])

                if len(frame) < 256:
                    print("Observed incorrect frame format, skipping...")
                    continue

                frames += 1
                print("Processing frame {}".format(frames))
                arr = array(frame)
                frame_dsc = self._load_frame_description()
                frame = Frame(arr, frame_dsc)
                frame.cluster()
                yield frame
        self.dsc_file.close()

    def _read_frame_header(self):
        lines = [self.dsc_file.readline() for _ in range(5)]

        frame_identifier = lines[0]
        frame_description = lines[1].split()
        data_type = frame_description[0].split('=')[-1]
        storage_type = frame_description[1]
        width = frame_description[2].split('=')[-1]
        height = frame_description[3].split('=')[-1]

    def _read_frame_field(self):
        regex = '\"(.*)\"\s\(\"(.*)\"\):'
        lines = [self.dsc_file.readline() for _ in range(4)]
        key = re.search(regex, lines[1]).group(1)
        value = lines[3].strip()

        return key, value

    def _load_frame_description(self):
        frame_dsc = {}
        self._read_frame_header()

        for _ in range(13):
            key, value = self._read_frame_field()
            frame_dsc[key] = value
        for _ in range(2):
            self.dsc_file.readline()

        return frame_dsc

    def frames(self):
        for frame in self._frames:
            yield frame

    def clusters(self):
        """
        Generator used to iterate over all clusters.
        :return:
        """
        for frame in self._frames:
            for cluster in frame.clusters:
                yield cluster


class Frame:
    def __init__(self, arr, description):
        self.arr = coo_matrix(arr)
        self.description = description
        self.acq_time = float(description['Acq time'])
        self.acq_start = float(description['Acq Serie Start time'])
        self.counts = 0
        self.clusters = []

    def cluster(self):
        frame = np.squeeze(np.asarray(self.arr.todense()))
        binary_img = binarize(frame)
        label_image = label(binary_img, connectivity=2)

        for region in regionprops(label_image, intensity_image=frame, coordinates='xy'):
            self.clusters.append(Cluster(region))
            self.counts += 1
        print(self.counts)

    def show_clusters(self):
        labeled, num_features = nlabel(self.arr.todense(),
                                       structure=self.connectivity_structure)
        clusters = find_objects(labeled)

        for cluster in clusters:

            plt.figure()
            plt.imshow(self.arr.todense()[cluster])

        plt.show()

    def show_frame(self):
        frame = self.arr.todense()
        binary_img = binarize(frame)
        label_image = label(binary_img, connectivity=2)
        image_label_overlay = label2rgb(label_image, image=frame)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.imshow(image_label_overlay)

        for region in regionprops(label_image, coordinates='xy'):
            r = cv.minAreaRect(region.coords)
            box = cv.boxPoints(r)
            box = np.flip(box)
            box = order_points(box)

            x_points = np.array([p[1] for p in region.coords])
            y_points = np.array([p[0] for p in region.coords])

            A = np.vstack([x_points, np.ones(len(x_points))]).T
            m, c = np.linalg.lstsq(A, y_points, rcond=None)[0]

            ax.plot(x_points, x_points * m + c, color='black', linewidth=1)
            rect = mpatches.Polygon(box, closed=True, fill=False, edgecolor='blue')

            ax.add_patch(rect)

            y0, x0 = region.centroid
            ax.plot(x0, y0, '.g', markersize=5)

            self.plot_intersections_with_bbox(box, m, c, ax)

        ax.set_axis_off()
        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_intersections_with_bbox(boxpoints, m, c, ax):
        intersections = []

        p1, p2, p3, p4 = boxpoints

        intersections.append(line_intersect(p1, p2, m, c))
        intersections.append(line_intersect(p2, p3, m, c))
        intersections.append(line_intersect(p3, p4, m, c))
        intersections.append(line_intersect(p4, p1, m, c))

        intersections = np.array(list(filter(lambda p: p is not None, intersections)))

        if len(intersections) > 2:
            # Choose points that maximize euclidean distance if there are more than 2 intersections
            edistance = dist.cdist(intersections, intersections, 'euclidean')
            i1, i2 = np.unravel_index(np.argmax(edistance), edistance.shape)
            intersections = [intersections[i1],
                             intersections[i2]]

        # assert (len(intersections) == 2)

        for intersection in intersections:
            x, y = intersection
            ax.plot(x, y, '.r', markersize=5)


class Cluster:
    # Calculated for our purposes
    min_area_box = None
    track_length = None
    intersections = None
    img = None

    # Calculated automatically by skimage (probably still useful).
    region_properties = None

    def __init__(self, region):
        self.calculate_cluster_parameters(region)

    def calculate_cluster_parameters(self, region):
        self.region_properties = region

        # Calculate minimum area bounding box
        r = cv.minAreaRect(region.coords)
        box = cv.boxPoints(r)
        box = np.flip(box)
        self.min_area_box = order_points(box)

        # Calculate intersections with bounding box
        x_points = np.array([p[1] for p in region.coords])
        y_points = np.array([p[0] for p in region.coords])

        A = np.vstack([x_points, np.ones(len(x_points))]).T
        m, c = np.linalg.lstsq(A, y_points, rcond=None)[0]

        intersections = intersections_with_bbox(box, m, c)

        if len(intersections) < 2:
            print("Failed to calculate a track length because too few intersections were received.")
            return

        self.track_length = dist.euclidean(intersections[0], intersections[1])
        self.intersections = intersections


def sparse_to_json(matrix):
    triples = np.array(list(zip(matrix.row, matrix.col, matrix.data)))

    return json.dumps(triples.tolist())


def sanitize_for_db(conv_dict):
    d = {}

    for key in conv_dict:
        if isinstance(conv_dict[key], np.ndarray):
            d[key] = json.dumps(conv_dict[key].tolist())
        elif isinstance(conv_dict[key], np.float):
            d[key] = float(conv_dict[key])
        elif isinstance(conv_dict[key], np.integer):
            d[key] = int(conv_dict[key])
        elif isinstance(conv_dict[key], tuple):
            d[key] = json.dumps(conv_dict[key])
        else:
            d[key] = conv_dict[key]

    d['intensity_image'] = json.dumps(conv_dict.intensity_image.tolist())

    return d


def insert_into_database(acq):
    Session = sessionmaker(bind=engine)
    session = Session()
    acquisition = AcquisitionModel(name=acq.filename)
    # session.add(acquisition)

    for i, frame in enumerate(acq.load()):
        db_frame = FrameModel()
        db_frame.frame_data = sparse_to_json(frame.arr)
        db_frame.acq_start = frame.acq_start
        db_frame.acq_time = frame.acq_time
        db_frame.description = json.dumps(frame.description)
        db_frame.counts = len(frame.clusters)

        for cluster in frame.clusters:
            db_cluster = ClusterModel()
            db_cluster.track_length = cluster.track_length
            db_cluster.intersections = json.dumps(np.array(cluster.intersections).tolist())
            db_cluster.min_area_box = json.dumps(cluster.min_area_box.tolist())
            # db_cluster.region_properties = json.dumps(convert_dict_arrays_to_list(cluster.region_properties))
            region_properties = sanitize_for_db(cluster.region_properties)

            for prop in region_properties:
                setattr(db_cluster, prop, region_properties[prop])

            db_frame.clusters.append(db_cluster)

        acquisition.frames.append(db_frame)
        print("Inserted frame {}".format(i))
    session.add(acquisition)
    session.commit()


if __name__ == '__main__':
    t0 = time.time()
    filename = '/home/lycurgus/Documents/HASP_2019_data/hasp_2019_medipix/mp_output-2019-09-05 10:17:16.pmf'
    acq = Acquisition(filename)

    t1 = time.time()

    frames = []
    print("Duration: {}".format(t1 - t0))

    for frame in acq.load():
        frames.append(frames)

    # insert_into_database(acq)
    import pickle
    f = open(filename + '.pkl', 'wb')
    pickle.dump(frames, )
