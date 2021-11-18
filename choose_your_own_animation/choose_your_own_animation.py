import datetime
import json
import os
import re
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional, Match

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QListView, QPushButton, QWidget, QSplitter, QSpinBox, QTextEdit, \
    QLineEdit
from krita import Krita, Document, Node, InfoObject, DockWidget, DockWidgetFactory, DockWidgetFactoryBase


class ChooseYourOwnAnimation(DockWidget):
    WINDOW_TITLE = "Choose Your Own Animation"

    ANIMATION_ROOT_LAYER_NAME = "Animation"
    PERFORMANCE_ROOT_LAYER_NAME = "Animation_Performance"
    FRAMES_ROOT_LAYER_NAME = 'Frames'
    BACKGROUND_LAYER_NAME = 'Background'

    INVALID_FILENAME_CHARACTERS = r'<>:"/\|?*'
    INVALID_FILENAME_CHARACTERS_PATTERN = re.compile(f"[{re.escape(INVALID_FILENAME_CHARACTERS)}]")
    COMMENT_PATTERN = re.compile(r"\[.*?]")
    LAYER_NAME_PATTERN = re.compile(r"(?P<name>\S+)\s*(?:\((?P<aliases>[^()]+)\))? - (?P<destinations>.+)")

    NODE_DATA = Qt.UserRole + 1

    KEY_FRAMES_DIRECTORY = "frames_directory"
    KEY_FRAMES_PER_SECOND = "frames_per_second"
    KEY_FRAMES_LIST = "frames"

    KEY_FRAMES_LIST_FRAME_KEY = "frame_name"
    KEY_FRAMES_LIST_FRAME_DURATION = "duration"

    DESCRIPTOR_FILE_SUFFIX = "_cyoa_descriptor.json"
    DESCRIPTOR_FRAMES_DIRECTORY = "cyoa_frames"
    FRAME_FULL_NAME_FILENAME = "frame_full_names.json"

    SCALING_METHOD_NONE = "None"

    def __init__(self):
        super().__init__()
        self.full_log = ""
        self.frame_name_to_node: Dict[str, Node] = {}
        self.frame_name_to_destination_nodes: Dict[str, List[Node]] = {}

        self.descriptor_frames = []

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

        # Number of frames to add Spinner.
        # TODO: Needs a label inside a... QHBoxLayout?
        self.frames_to_add_spinner = QSpinBox()
        self.frames_to_add_spinner.setMinimum(1)
        self.frames_to_add_spinner.setValue(2)
        left_layout.addWidget(self.frames_to_add_spinner)

        self.current_frame_name_widget = QLineEdit()
        self.current_frame_name_widget.editingFinished.connect(self.refresh_choices_if_modified)
        left_layout.addWidget(self.current_frame_name_widget)

        # Extra buttons.  TODO Put all controls in QGridLayout
        initializer_box = QWidget()
        initializer_layout = QHBoxLayout()
        initializer_box.setLayout(initializer_layout)
        left_layout.addWidget(initializer_box)

        self.button_reload = QPushButton("Initialize / Reload")
        self.button_reload.clicked.connect(self.reload_from_file)
        initializer_layout.addWidget(self.button_reload)

        self.button_clear_log = QPushButton("Clear Log")
        self.button_clear_log.clicked.connect(self.clear_log)
        initializer_layout.addWidget(self.button_clear_log)

        # TEMP AREA START
        self.temp_button = QPushButton("Temp")
        initializer_layout.addWidget(self.temp_button)
        self.temp_button.clicked.connect(self.do_a_thing)
        # End Extra Buttons

        self.action_line_edit = QLineEdit()
        left_layout.addWidget(self.action_line_edit)
        self.action_button = QPushButton("Do the Krita action in the text line above.")
        left_layout.addWidget(self.action_button)
        self.action_button.clicked.connect(self.do_action)
        # TEMP AREA END

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

    # noinspection PyPep8Naming
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

    def do_a_thing(self) -> None:
        self.log_info("Doing the thing!")
        active_document = self.get_active_document()
        if active_document:
            self.log_info(active_document.fileName())
            pass
        self.log_info("Exiting Doing the thing function.")

    def do_action(self) -> None:
        action = self.action_line_edit.text()
        self.log_info(f"Doing: {action}")
        self.do_krita_action(action)
        self.log_info("Done.")

    def reload_from_file(self) -> None:
        active_document = self.get_active_document()
        if not active_document:
            self.log_error("Make or open a document.")
            return

        # TODO disable controls
        if not os.path.exists(self._get_descriptor_filepath()):
            self.descriptor_frames = []
            self._save_descriptor()

        self.refresh_frame_index()

        frames_directory = self._get_frames_directory()
        if not os.path.exists(frames_directory):
            os.makedirs(frames_directory)
            self._export_frames()

        self._load_descriptor()
        self._regenerate_animation_layer()
        # TODO enable controls

    def _get_frames_directory(self) -> str:
        active_document = self.get_active_document()
        krita_directory = os.path.dirname(active_document.fileName())
        return os.path.join(krita_directory, self.DESCRIPTOR_FRAMES_DIRECTORY)

    def _get_descriptor_filepath(self) -> str:
        active_document = self.get_active_document()
        krita_filename = os.path.basename(active_document.fileName())
        descriptor_filename = krita_filename + self.DESCRIPTOR_FILE_SUFFIX
        krita_directory = os.path.dirname(active_document.fileName())
        return os.path.join(krita_directory, descriptor_filename)

    def _save_descriptor(self) -> None:
        descriptor = {self.KEY_FRAMES_DIRECTORY: self.DESCRIPTOR_FRAMES_DIRECTORY,
                      self.KEY_FRAMES_PER_SECOND: self.get_active_document().framesPerSecond(),
                      self.KEY_FRAMES_LIST: self.descriptor_frames}
        with open(self._get_descriptor_filepath(), 'w') as outfile:
            json.dump(descriptor, outfile)
        self._update_animation_times()

    def _load_descriptor(self) -> None:
        with open(self._get_descriptor_filepath(), 'r') as outfile:
            descriptor = json.load(outfile)
            self.get_active_document().setFramesPerSecond(descriptor[self.KEY_FRAMES_PER_SECOND])
            self.descriptor_frames = descriptor[self.KEY_FRAMES_LIST]
        self._update_animation_times()

        ending_frame_name = self.descriptor_frames[-1][self.KEY_FRAMES_LIST_FRAME_KEY] if self.descriptor_frames else ""
        self.update_current_frame_name(ending_frame_name)

    def _update_animation_times(self) -> None:
        self.get_active_document().setFullClipRangeStartTime(0)
        self.get_active_document().setFullClipRangeEndTime(self.calculate_animation_end_time())

    def calculate_animation_end_time(self) -> int:
        frame_count = self._get_frame_count()
        return frame_count - 1 if frame_count > 0 else 0

    def update_current_frame_name(self, frame_name: str) -> None:
        self.current_frame_name_widget.setText(frame_name)
        self.refresh_choices()

    def _get_frame_count(self) -> int:
        return sum([frame[self.KEY_FRAMES_LIST_FRAME_DURATION] for frame in self.descriptor_frames])

    def _export_frames(self) -> None:
        full_names_filepath = os.path.join(self._get_frames_directory(), self.FRAME_FULL_NAME_FILENAME)
        full_names = {frame_name: node.name() for frame_name, node in self.frame_name_to_node.items()}
        with open(full_names_filepath, 'w') as outfile:
            json.dump(full_names, outfile)

        for frame_name, node in self.frame_name_to_node.items():
            self.export_node(self.get_active_document(), node, self.frame_name_to_filepath(frame_name))

    def export_node(self, document: Document, node: Node, filepath: str) -> None:
        resolution = document.resolution()
        info = InfoObject()
        info.setProperty("alpha", True)
        info.setProperty("compression", 9)
        info.setProperty("forceSRGB", False)
        info.setProperty("indexed", False)
        info.setProperty("interlaced", False)
        info.setProperty("saveSRGBProfile", False)
        info.setProperty("transparencyFillcolor", [0, 0, 0])

        Krita.instance().setBatchmode(True)
        self.log_info(f"Exporting: {filepath}")
        node.save(filepath, resolution, resolution, info)
        self.log_info(f"Exported: {filepath}")
        Krita.instance().setBatchmode(False)

    def _regenerate_animation_layer(self) -> None:
        active_document = self.get_active_document()
        frames_group = active_document.nodeByName(self.FRAMES_ROOT_LAYER_NAME)
        frames_group.setVisible(False)
        background_layer = active_document.nodeByName(self.BACKGROUND_LAYER_NAME)

        self.log_info("Generating animation.")
        self.remove_layer_if_exists(active_document, self.ANIMATION_ROOT_LAYER_NAME)
        animation_layer = active_document.createGroupLayer(self.ANIMATION_ROOT_LAYER_NAME)
        active_document.rootNode().addChildNode(animation_layer, frames_group)
        self._regenerate_child_layers(active_document, animation_layer)

        self.remove_layer_if_exists(active_document, self.PERFORMANCE_ROOT_LAYER_NAME)
        performance_layer = animation_layer.clone()
        performance_layer.setName(self.PERFORMANCE_ROOT_LAYER_NAME)
        performance_layer.setVisible(False)
        performance_layer.setCollapsed(True)
        active_document.rootNode().addChildNode(performance_layer, background_layer)

        active_document.setActiveNode(animation_layer)
        animation_layer.setPinnedToTimeline(True)

        if animation_layer.childNodes():
            animation_layer.childNodes()[-1].setVisible(True)
        # self.do_krita_action('convert_group_to_animated')
        # active_document.setCurrentTime(self.calculate_animation_end_time())
        self.log_info("Animation generated.")

    def _append_animation_frames(self, frame_name: str, duration: int) -> None:
        self.log_info(f"Appending {duration} frame(s): {frame_name}")

        active_document = self.get_active_document()
        performance_layer = active_document.nodeByName(self.PERFORMANCE_ROOT_LAYER_NAME)
        if not performance_layer:
            self.log_warning("Performance layer expected but not found. Regenerating.")
            # Disable controls
            self._regenerate_animation_layer()
            # Enable controls
            performance_layer = active_document.nodeByName(self.PERFORMANCE_ROOT_LAYER_NAME)

        frame_insert_index = self._get_frame_count()
        self.descriptor_frames.append({
            self.KEY_FRAMES_LIST_FRAME_KEY: frame_name,
            self.KEY_FRAMES_LIST_FRAME_DURATION: duration,
        })
        self._save_descriptor()
        new_child_nodes = self._create_child_nodes(active_document, frame_name, duration, frame_insert_index)

        # Work around bug in "setChildNodes(performance_layer.childNodes() + new_child_nodes)"
        # Somehow trying to use setChildNodes allows the 0 index item to migrate to before the new nodes.
        prev_child_nodes = performance_layer.childNodes()
        prev_node = prev_child_nodes[-1] if prev_child_nodes else None
        for node in new_child_nodes:
            performance_layer.addChildNode(node, prev_node)
            prev_node = node

        self.remove_layer_if_exists(active_document, self.ANIMATION_ROOT_LAYER_NAME)
        animation_layer = performance_layer.clone()
        animation_layer.setName(self.ANIMATION_ROOT_LAYER_NAME)
        animation_layer.setVisible(True)
        frames_group = active_document.nodeByName(self.FRAMES_ROOT_LAYER_NAME)
        active_document.rootNode().addChildNode(animation_layer, frames_group)

        active_document.setActiveNode(animation_layer)
        animation_layer.setPinnedToTimeline(True)
        # animation_layer.setCollapsed(False)

        if animation_layer.childNodes():
            animation_layer.childNodes()[-1].setVisible(True)
        # self.do_krita_action('convert_group_to_animated')
        # active_document.setCurrentTime(self.calculate_animation_end_time())
        self.log_info(f"Appended.")

    @staticmethod
    def remove_layer_if_exists(document: Document, layer_name: str) -> None:
        layer = document.nodeByName(layer_name)
        if layer:
            layer.remove()

    def _regenerate_child_layers(self, document: Document, root_animation_layer: Node) -> None:
        current_frame = 0
        child_nodes = []
        for frame in self.descriptor_frames:
            frame_name = frame[self.KEY_FRAMES_LIST_FRAME_KEY]
            duration = frame[self.KEY_FRAMES_LIST_FRAME_DURATION]
            child_nodes.extend(self._create_child_nodes(document, frame_name, duration, current_frame))
            current_frame += duration
        root_animation_layer.setChildNodes(child_nodes)

    def _create_child_nodes(self, active_document: Document, frame_name: str, duration: int, current_frame: int):
        frame_count = self._get_frame_count()
        frame_count_digits = len(str(frame_count))
        child_nodes = []
        frame_filepath = self.frame_name_to_filepath(frame_name)
        previous_layer = None
        for i in range(0, duration):
            layer_name = str(current_frame).zfill(frame_count_digits)
            if i == 0:
                file_layer = active_document.createFileLayer(layer_name, frame_filepath, self.SCALING_METHOD_NONE)
                previous_layer = file_layer
            else:
                file_layer = active_document.createCloneLayer(layer_name, previous_layer)
            file_layer.setVisible(False)
            child_nodes.append(file_layer)
            current_frame += 1
        return child_nodes

    def frame_name_to_filepath(self, frame_name: str) -> str:
        return os.path.join(self._get_frames_directory(), frame_name + ".png")

    def refresh_frame_index(self) -> None:
        self.log_info(f"Refreshing future frame index...")
        self.frame_name_to_node, self.frame_name_to_destination_nodes = self.calculate_frame_destinations()
        self.log_info(f"Done refreshing future frame index.")

    def calculate_frame_destinations(self) -> Tuple[Dict[str, Node], Dict[str, List[Node]]]:
        frame_name_to_node, frame_name_to_aliases, frame_name_to_destinations = self.get_layer_information()

        # What Node is being talked about when an alias is given. Since anything can claim an alias, we get a Set.
        destination_name_to_frame_name: Dict[str, Set[str]] = defaultdict(set)
        for frame_name, aliases in frame_name_to_aliases.items():
            for alias in aliases:
                destination_name_to_frame_name[alias].add(frame_name)

        # Finally, assemble the data structure we can query for what frames come next.
        frame_name_to_destination_nodes: Dict[str, List[Node]] = {}
        for frame_name, aliases in frame_name_to_destinations.items():
            unique_destination_frame_names: Set[str] = set()
            for alias in aliases:
                if alias not in destination_name_to_frame_name:
                    self.log_warning(f"Layer not found for alias: {alias}")
                    continue
                unique_destination_frame_names.update(destination_name_to_frame_name[alias])

            unique_destination_nodes = [frame_name_to_node[alias] for alias in unique_destination_frame_names]
            frame_name_to_destination_nodes[frame_name] = unique_destination_nodes

        return frame_name_to_node, frame_name_to_destination_nodes

    def get_layer_information(self) -> Tuple[Dict[str, Node], Dict[str, List[str]], Dict[str, List[str]]]:
        leaf_nodes = self.get_leaf_nodes()

        frame_name_to_node: Dict[str, Node] = {}
        frame_name_to_aliases: Dict[str, List[str]] = {}
        frame_name_to_destinations: Dict[str, List[str]] = {}
        for leaf in leaf_nodes:
            match = self.extract_strings_from_node(leaf)
            if not match:
                self.log_warning(f"Skipping incorrectly named layer: {leaf.name()}")
                continue

            frame_name = match.group('name')
            frame_aliases = match.group('aliases')
            frame_destinations = match.group('destinations')
            if self.INVALID_FILENAME_CHARACTERS_PATTERN.search(frame_name):
                self.log_warning(f"Skipping layer (invalid character): {frame_name}")
                self.log_warning(f'Invalid character list: {" ".join(self.INVALID_FILENAME_CHARACTERS)}')
                continue

            if frame_name in frame_name_to_node:
                self.log_warning(f"Skipping layer (duplicate name): {frame_name}")
                continue
            frame_name_to_node[frame_name] = leaf
            frame_name_to_aliases[frame_name] = frame_aliases.split(" ") if frame_aliases else []
            frame_name_to_aliases[frame_name].extend([frame_name])  # A layer name is an alias to itself.
            frame_name_to_destinations[frame_name] = frame_destinations.split(" ") if frame_destinations else []

        return frame_name_to_node, frame_name_to_aliases, frame_name_to_destinations

    def extract_strings_from_node(self, node: Node) -> Optional[Match]:
        name_with_removed_comments = self.COMMENT_PATTERN.sub("", node.name())
        match = self.LAYER_NAME_PATTERN.fullmatch(name_with_removed_comments)
        return match

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
        if not frame_name:
            destination_nodes = self.frame_name_to_node.values()
        elif frame_name not in self.frame_name_to_destination_nodes:
            self.log_error(f"No frames in index for: {frame_name}")
            return
        else:
            destination_nodes = self.frame_name_to_destination_nodes[frame_name]

        self.frames_model.clear()
        # sorted(destination_nodes, key=attrgetter('name'))
        for dn in destination_nodes:
            destination_frame_icon = QIcon(QPixmap.fromImage(dn.thumbnail(128, 128)))
            destination_frame_name = self.extract_strings_from_node(dn).group('name')
            item = QStandardItem(destination_frame_icon, destination_frame_name)
            item.setData(dn, self.NODE_DATA)
            self.frames_model.appendRow(item)

        self.log_info("Finished refreshing future frame choices.")

    def choice_double_clicked(self, clicked_index) -> None:
        active_document = self.get_active_document()
        if not active_document:
            self.log_error("Make or open the document.")

        node_of_clicked_choice = clicked_index.data(self.NODE_DATA)
        frame_name = self.extract_strings_from_node(node_of_clicked_choice).group('name')
        duration = self.frames_to_add_spinner.value()

        self._append_animation_frames(frame_name, duration)
        self.update_current_frame_name(frame_name)

    @staticmethod
    def do_krita_action(action_name: str) -> None:
        Krita.instance().action(action_name).trigger()

    @staticmethod
    def get_active_document() -> Optional[Document]:
        return Krita.instance().activeDocument()


DOCKER_ID = "choose_your_own_animation"
dock_widget_factory = DockWidgetFactory(DOCKER_ID,
                                        DockWidgetFactoryBase.DockRight,
                                        ChooseYourOwnAnimation)
instance = Krita.instance()
instance.addDockWidgetFactory(dock_widget_factory)
