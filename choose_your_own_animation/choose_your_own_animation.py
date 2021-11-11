import datetime
import re
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QListView, QPushButton, QWidget, QSplitter, QSpinBox, QTextEdit, \
    QLineEdit
from krita import Krita, Document, Node, DockWidget, DockWidgetFactory, DockWidgetFactoryBase


class ChooseYourOwnAnimation(DockWidget):
    WINDOW_TITLE = "Choose Your Own Animation"
    ANIMATION_ROOT_LAYER_NAME = "Animation"
    FRAMES_ROOT_LAYER_NAME = 'Frames'
    COMMENT_PATTERN = re.compile(r"\[.*?]")
    LAYER_NAME_PATTERN = re.compile(r"(?P<name>\S+)\s*(?:\((?P<aliases>[^()]+)\))? - (?P<dests>.+)")

    def __init__(self):
        super().__init__()
        self.full_log = ""
        self.frame_name_to_node: Dict[str, Node] = {}
        self.frame_name_to_destination_nodes: Dict[str, List[Node]] = {}

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

        self.current_frame_name_widget = QLineEdit()
        self.current_frame_name_widget.editingFinished.connect(self.refresh_choices_if_modified)
        left_layout.addWidget(self.current_frame_name_widget)

        self.button_refresh = QPushButton("Refresh Frame Index")
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
        self.future_frames_list.doubleClicked.connect(self.choice_double_clicked)

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
        self.scroll_log_to_bottom()

    def clear_log(self) -> None:
        self.full_log = ""
        self.log_text_area.setPlainText("")

    def scroll_log_to_bottom(self) -> None:
        vertical_scroll_bar = self.log_text_area.verticalScrollBar()
        vertical_scroll_bar.setValue(vertical_scroll_bar.maximum())

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

    def refresh(self) -> None:
        self.refresh_frame_index()
        self.refresh_choices()

    def refresh_frame_index(self) -> None:
        self.log_info(f"Refreshing future frame index...")
        frame_name_to_node, frame_name_to_aliases, frame_name_to_destinations = self.get_layer_information()

        self.frame_name_to_node = frame_name_to_node

        # What Node is being talked about when an alias is given. Since anything can claim an alias, we get a Set.
        destination_name_to_frame_name: Dict[str, Set[str]] = defaultdict(set)
        for frame_name, aliases in frame_name_to_aliases.items():
            for alias in aliases:
                destination_name_to_frame_name[alias].add(frame_name)

        # Finally, assemble the data structure we can query for what frames come next.
        self.frame_name_to_destination_nodes.clear()
        for frame_name, aliases in frame_name_to_destinations.items():
            destination_frame_names: Set[str] = set()
            for alias in aliases:
                if alias not in destination_name_to_frame_name:
                    self.log_warning(f"Layer not found for alias: {alias}")
                    continue
                destination_frame_names.update(destination_name_to_frame_name[alias])

            unique_destination_nodes = [self.frame_name_to_node[alias] for alias in destination_frame_names]
            self.frame_name_to_destination_nodes[frame_name] = unique_destination_nodes

        self.log_info(f"Done refreshing future frame index.")

    def get_layer_information(self) -> Tuple[Dict[str, Node], Dict[str, List[str]], Dict[str, List[str]]]:
        leaf_nodes = self.get_leaf_nodes()

        frame_name_to_node: Dict[str, Node] = {}
        frame_name_to_aliases: Dict[str, List[str]] = {}
        frame_name_to_destinations: Dict[str, List[str]] = {}
        for leaf in leaf_nodes:
            name_with_removed_comments = self.COMMENT_PATTERN.sub("", leaf.name())
            match = self.LAYER_NAME_PATTERN.fullmatch(name_with_removed_comments)
            if not match:
                self.log_warning(f"Skipping incorrectly named layer: {leaf.name()}")
                continue

            frame_name = match.group('name')
            frame_aliases = match.group('aliases')
            frame_destinations = match.group('dests')
            if frame_name in frame_name_to_node:
                self.log_warning(f"Skipping layer with duplicate name: {frame_name}")
                continue
            frame_name_to_node[frame_name] = leaf
            frame_name_to_aliases[frame_name] = frame_aliases.split(" ") if frame_aliases else []
            frame_name_to_aliases[frame_name].extend([frame_name])  # A layer name is an alias to itself.
            frame_name_to_destinations[frame_name] = frame_destinations.split(" ") if frame_destinations else []

        return frame_name_to_node, frame_name_to_aliases, frame_name_to_destinations

    def get_leaf_nodes(self) -> List[Node]:
        doc = self.get_active_document()
        if not doc:
            self.log_error("Make or open a document.")
            return []

        frames_group = doc.nodeByName(self.FRAMES_ROOT_LAYER_NAME)
        if not frames_group:
            self.log_error(f"Make a Group named '{self.FRAMES_ROOT_LAYER_NAME}'.")
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

    def refresh_choices_if_modified(self) -> None:
        if self.current_frame_name_widget.isModified():
            self.current_frame_name_widget.setModified(False)
            self.refresh_choices()

    def refresh_choices(self) -> None:
        self.log_info("Refreshing future frame choices...")

        frame_name = self.current_frame_name_widget.text()
        if frame_name not in self.frame_name_to_destination_nodes:
            self.log_error(f"No frames in index for: {frame_name}")
            return

        self.frames_model.clear()
        # sorted(, key=attrgetter('name'))   # <--How to sort the Nodes by name later, for display.
        destination_nodes = self.frame_name_to_destination_nodes[frame_name]
        for dn in destination_nodes:
            frame_icon = QIcon(QPixmap.fromImage(dn.thumbnail(128, 128)))
            self.frames_model.appendRow(QStandardItem(frame_icon, dn.name()))

        self.log_info("Finished refreshing future frame choices.")

    def choice_double_clicked(self, clicked_index) -> None:
        self.log_info(f"User picked index {clicked_index}")

    @staticmethod
    def get_active_document() -> Optional[Document]:
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
        animation_layer = self.get_or_create_layer(self.ANIMATION_ROOT_LAYER_NAME)
        if not animation_layer.animated():
            animation_layer.enableAnimation()
        return animation_layer


DOCKER_ID = "choose_your_own_animation"
dock_widget_factory = DockWidgetFactory(DOCKER_ID,
                                        DockWidgetFactoryBase.DockRight,
                                        ChooseYourOwnAnimation)
instance = Krita.instance()
instance.addDockWidgetFactory(dock_widget_factory)
