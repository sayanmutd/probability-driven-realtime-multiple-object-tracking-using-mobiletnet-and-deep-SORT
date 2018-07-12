# -*- coding: utf-8 -*-
"""
Created on Sun Jun 24 14:53:30 2018

@author: Administrator
"""
from __future__ import division, print_function, absolute_import

import configparser
import numpy as np

from .deep_sort.application_util import preprocessing, visualization
from .deep_sort.deep_sort import nn_matching, linear_assignment
from .deep_sort.deep_sort.detection import Detection
from .deep_sort.deep_sort.tracker import Tracker
from .deep_sort.tools.generate_detections import create_box_encoder

from .tracker_template import Tracker_Template
from .utils import mot_challenge_util

class Tracker_Deep_Sort(Tracker_Template):
    def __init__(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)

        self.sequence_dir = config.get('deep_sort', 'sequence_dir')
        self.detection_file = config.get('deep_sort', 'detection_file')
        self.is_output = config.get('deep_sort', 'is_output') == 'True'
        self.output_file = config.get('deep_sort', 'output_file')
        self.min_confidence = float(config.get('deep_sort', 'min_confidence'))
        self.nms_max_overlap = float(config.get('deep_sort', 'nms_max_overlap'))
        self.min_detection_height = float(config.get('deep_sort', 'min_detection_height'))
        self.display = config.get('deep_sort', 'display') == 'True'
        max_cosine_distance = float(config.get('deep_sort', 'max_cosine_distance'))
        nn_budget = int(config.get('deep_sort', 'nn_budget'))
        model_filename = config.get('deep_sort', 'model_path')

        self.encoder = create_box_encoder(model_filename, batch_size=1)
        metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
        self.tracker = Tracker(metric)

    def _create_detections(self, detection_mat, frame_idx, min_height=0):
        """Create detections for given frame index from the raw detection matrix.

        Parameters
        ----------
        detection_mat : ndarray
            Matrix of detections. The first 10 columns of the detection matrix are
            in the standard MOTChallenge detection format. In the remaining columns
            store the feature vector associated with each detection.
        frame_idx : int
            The frame index.
        min_height : Optional[int]
            A minimum detection bounding box height. Detections that are smaller
            than this value are disregarded.

        Returns
        -------
        List[tracker.Detection]
            Returns detection responses at given frame index.
        """
        frame_indices = detection_mat[:, 0].astype(np.int)
        mask = frame_indices == frame_idx

        detection_list = []
        for row in detection_mat[mask]:
            bbox, confidence, feature = row[2:6], row[6], row[10:]
            if bbox[3] < min_height:
                continue
            detection_list.append(Detection(bbox, confidence, feature))
        return detection_list

    def start_tracking(self, frame, boxes, scores):

        features = self.encoder(frame, boxes)
        # score to 1.0 here).
        detections = [Detection(bbox, score, feature) for bbox, score, feature in zip(boxes, scores, features)]
        #detections = [Detection(bbox, 1.0) for bbox in zip(boxs)]
        # Run non-maxima suppression.
        boxes = np.array([d.tlwh for d in detections])
        scores = np.array([d.confidence for d in detections])
        indices = preprocessing.non_max_suppression(boxes, self.nms_max_overlap, scores)
        detections = [detections[i] for i in indices]
        self.tracker.predict()
        self.tracker.update(detections)

        return self.tracker, detections

    def is_detection_needed(self):
        return linear_assignment.is_tracker_in_low_prob

    def set_detecion_needed(self, value):
        linear_assignment.is_tracker_in_low_prob = value