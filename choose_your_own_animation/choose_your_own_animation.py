import datetime
import re
from collections import defaultdict
from typing import List, Dict, Set

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QListView, QPushButton, QWidget, QSplitter, QSpinBox, QTextEdit
from krita import Krita, Node, DockWidget, DockWidgetFactory, DockWidgetFactoryBase


class ChooseYourOwnAnimation(DockWidget):
    WINDOW_TITLE = "Choose Your Own Animation"
    ANIMATION_LAYER_NAME = "Animation"

    def __init__(self):
        super().__init__()
        self.full_log = ""
        self.layer_name_to_destination_nodes: Dict[str, Set[Node]] = {}

        self.setWindowTitle(self.WINDOW_TITLE)
        base_widget = QWidget()
        self.setWidget(base_widget)

        base_horizontal_layout = QHBoxLayout()
        base_widget.setLayout(base_horizontal_layout)

        base_splitter = QSplitter()
        base_horizontal_layout.addWidget(base_splitter)

        # Left side
        left_box = QWidget()
        left_layout = QVBoxLayout()
        left_box.setLayout(left_layout)
        base_splitter.addWidget(left_box)

        # Add Frames Button
        self.add_frames_button = QPushButton("Add Frame(s)")
        # self.add_frames_button.clicked.connect(self.add_frames_slot)
        left_layout.addWidget(self.add_frames_button)
        self.add_frames_button.setDisabled(True)

        # Current Frame Textbox
        # Goes here. Also will need a label, like the spinner below.

        # Number of frames to add Spinner. Probably needs to be on 'self' to get value.
        # TODO: Needs a label inside a... QHBoxLayout?
        frames_to_add_spinner = QSpinBox()
        frames_to_add_spinner.setMinimum(1)
        frames_to_add_spinner.setValue(2)
        left_layout.addWidget(frames_to_add_spinner)

        self.button_refresh = QPushButton("Refresh Frames")
        self.button_refresh.clicked.connect(self.refresh)
        left_layout.addWidget(self.button_refresh)

        self.button_clear_log = QPushButton("Clear Log")
        self.button_clear_log.clicked.connect(self.clear_log)
        left_layout.addWidget(self.button_clear_log)

        self.temp_button = QPushButton("Temp")
        left_layout.addWidget(self.temp_button)
        self.temp_button.clicked.connect(self.do_a_thing)

        self.log_text_area = QTextEdit()
        self.log_text_area.setReadOnly(True)
        left_layout.addWidget(self.log_text_area)

        # Right side
        future_frames_box = QWidget()
        base_splitter.addWidget(future_frames_box)
        right_layout = QVBoxLayout()
        future_frames_box.setLayout(right_layout)

        # We don't need any "live update". A refresh button will do just fine.
        self.future_frames_list = QListView()
        self.future_frames_list.setViewMode(QListView.ViewMode.IconMode)
        self.future_frames_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.future_frames_list.setIconSize(QSize(128, 128))
        self.future_frames_list.setResizeMode(QListView.Adjust)
        # self.future_frames_list.doubleClicked.connect()

        self.frames_model = QStandardItemModel()
        self.future_frames_list.setModel(self.frames_model)
        right_layout.addWidget(self.future_frames_list)

    def canvasChanged(self, canvas):
        # TODO this is not "document changed". Should refresh future_frames when document loads.
        pass

    def log_info(self, text: str) -> None:
        self._log("INFO", text)

    def log_warning(self, text: str) -> None:
        self._log("WARN", text)

    def log_error(self, text: str) -> None:
        self._log("ERROR", text)

    def _log(self, prefix: str, text: str) -> None:
        time = datetime.datetime.now()
        self.full_log += f"{time} - {prefix} - {text}\n"
        self.log_text_area.setPlainText(self.full_log)

    def clear_log(self) -> None:
        self.full_log = ""
        self.log_text_area.setPlainText("")

    def do_a_thing(self):
        self.log_info("Doing the thing!")
        active_doc = self.get_active_document()
        if active_doc:
            temp_layer = self.get_or_create_layer("Temp")

            temp_image = temp_layer.thumbnail(128, 128)
            temp_icon = QIcon(QPixmap.fromImage(temp_image))
            temp_item = QStandardItem(temp_icon, "PlaceholderText")

            temp2_layer = self.get_or_create_layer("Temp2")
            x = 0
            y = 0
            w = active_doc.width()
            h = active_doc.height()
            dst_layer = temp2_layer
            pixel_data_copy = self.get_node_pixel_projection("Temp")
            dst_layer.setPixelData(pixel_data_copy, x, y, w, h)

            self.frames_model.appendRow(temp_item)
        self.log_info("Exiting Doing the thing function.")

    def refresh(self):
        self.log_info(f"Refreshing future frame index...")
        leaf_nodes = self.get_leaf_nodes()

        comment_pattern = re.compile(r"\[.*?]")
        layer_name_pattern = re.compile(r"(?P<name>\S+)\s*(?:\((?P<aliases>[^()]+)\))? - (?P<dests>.+)")

        layer_name_to_node: Dict[str, Node] = {}
        layer_name_to_aliases: Dict[str, List[str]] = {}
        layer_name_to_destinations: Dict[str, List[str]] = {}
        for leaf in leaf_nodes:
            name_with_removed_comments = comment_pattern.sub("", leaf.name())
            match = layer_name_pattern.fullmatch(name_with_removed_comments)
            if not match:
                self.log_warning(f"Skipping incorrectly named layer: {leaf.name()}")
                continue

            layer_name = match.group('name')
            layer_aliases = match.group('aliases')
            layer_destinations = match.group('dests')
            if layer_name in layer_name_to_node:
                self.log_warning(f"Skipping layer with duplicate name: {layer_name}")
                continue
            layer_name_to_node[layer_name] = leaf
            layer_name_to_aliases[layer_name] = layer_aliases.split(" ") if layer_aliases else []
            layer_name_to_aliases[layer_name].extend([layer_name])  # A layer name is an alias to itself.
            layer_name_to_destinations[layer_name] = layer_destinations.split(" ") if layer_destinations else []

        # What Node is being talked about when an alias is given. Since anything can claim an alias, we get a Set.
        destination_name_to_nodes: Dict[str, Set[Node]] = defaultdict(set)
        for layer_name, aliases in layer_name_to_aliases.items():
            destination_node = layer_name_to_node[layer_name]
            for alias in aliases:
                destination_name_to_nodes[alias] += destination_node

        # Finally, assemble the data structure we can query for what frames come next.
        self.layer_name_to_destination_nodes.clear()
        for layer_name, aliases in layer_name_to_destinations.items():
            destination_nodes = set()
            for alias in aliases:
                if alias not in destination_name_to_nodes:
                    self.log_warning(f"Layer not found for alias: {alias}")
                    continue
                destination_nodes.update(destination_name_to_nodes[alias])
            self.layer_name_to_destination_nodes[layer_name] = destination_nodes

        self.log_info(f"Done refreshing future frame index.")
        # sorted(layers, key=attrgetter('name'))   # <--How to sort the Nodes by name later, for display.

    def get_leaf_nodes(self) -> List[Node]:
        doc = self.get_active_document()
        if not doc:
            self.log_error("Make or open a document.")
            return []

        frames_group = doc.nodeByName('Frames')
        if not frames_group:
            self.log_error("Make a Group named 'Frames'.")
            return []

        return self.recursively_get_leaf_nodes(frames_group)

    def recursively_get_leaf_nodes(self, root_node: Node) -> List[Node]:
        result = []
        if root_node.childNodes():
            for c in root_node.childNodes():
                result.extend(self.recursively_get_leaf_nodes(c))
        else:
            result.append(root_node)
        return result

    @staticmethod
    def get_active_document():
        return Krita.instance().activeDocument()

    def get_node_pixel_projection(self, node_name):
        active_doc = self.get_active_document()
        x = 0
        y = 0
        w = active_doc.width()
        h = active_doc.height()
        src_layer = active_doc.nodeByName(node_name)
        if not src_layer:
            self.log_warning(f"Could not find {node_name}")
            return None
        pixel_data = src_layer.projectionPixelData(x, y, w, h)
        return pixel_data

    @classmethod
    def get_or_create_layer(cls, name):
        active_doc = cls.get_active_document()
        layer = active_doc.nodeByName(name)
        if not layer:
            layer = active_doc.createNode(name, "paintLayer")
            active_doc.rootNode().addChildNode(layer, None)
        return layer

    def get_or_create_animation_layer(self):
        animation_layer = self.get_or_create_layer(self.ANIMATION_LAYER_NAME)
        if not animation_layer.animated():
            animation_layer.enableAnimation()
        return animation_layer


DOCKER_ID = "choose_your_own_animation"
dock_widget_factory = DockWidgetFactory(DOCKER_ID,
                                        DockWidgetFactoryBase.DockRight,
                                        ChooseYourOwnAnimation)
instance = Krita.instance()
instance.addDockWidgetFactory(dock_widget_factory)
