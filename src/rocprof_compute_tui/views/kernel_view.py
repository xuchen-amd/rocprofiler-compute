"""
Panel Widget Modules
-------------------
Contains the panel widgets used in the main layout.
"""

from typing import Optional

from textual import on
from textual.containers import Container, VerticalScroll
from textual.widgets import Label, RadioButton, RadioSet

from config import rocprof_compute_home
from rocprof_compute_tui.widgets.collapsibles import build_all_sections


class KernelView(Container):
    """Center panel with analysis results split into two scrollable sections."""

    DEFAULT_CSS = """
    KernelView {
        layout: vertical;
    }

    #top-container {
        height: 1fr;
        border: none;
        margin-top: 1;
    }

    #bottom-container {
        height: 4fr;
        border: none;
        margin-top: 2;
    }

    .kernel-table-header {
        background: $primary;
        color: $text;
        text-style: bold;
        padding: 0 1;
        offset: 5 0;
        margin-top: 1;
    }

    .kernel-row {
        padding: 0 1;
        border-bottom: solid $border;
    }

    RadioSet {
        border: solid $border;
    }
    """

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(id="kernel-view")
        self.dfs = {}
        self.top_kernel = []
        self.current_selection = None

        self.config_path = config_path or (
            rocprof_compute_home
            / "rocprof_compute_tui"
            / "utils"
            / "kernel_view_config.yaml"
            if rocprof_compute_home
            else None
        )

    def compose(self):
        """
        Compose the split panel layout with two scrollable containers.
        """
        with VerticalScroll(id="top-container"):
            yield Label(
                "Open a workload directory to run analysis and view individual kernel analysis results.",
                classes="placeholder",
            )

        with VerticalScroll(id="bottom-container"):
            # empty on init
            pass

    def update_results(self, per_kernel_dfs, top_kernels) -> None:
        self.dfs = per_kernel_dfs
        self.top_kernel = top_kernels

        top_container = self.query_one("#top-container", VerticalScroll)
        top_container.remove_children()

        if not self.top_kernel:
            top_container.mount(Label("No kernels available", classes="placeholder"))
            return

        # Build and mount components
        keys = self._get_sorted_keys()
        header_text = " | ".join(f"{key:25}" for key in keys)
        top_container.mount(Label(header_text, classes="kernel-table-header"))

        radio_buttons = []
        for i, kernel in enumerate(self.top_kernel):
            row_text = " | ".join(
                f"{str(kernel.get(key, 'N/A'))[:18]:25}" for key in keys
            )
            button = RadioButton(row_text, id=f"kernel-{i}")
            button.kernel_data = kernel
            radio_buttons.append(button)

        top_container.mount(RadioSet(*radio_buttons))

        self.current_selection = self.top_kernel[0]["Kernel_Name"]
        self.update_bottom_content()

    def update_view(self, message: str, log_level: str) -> None:
        if not hasattr(self, "status_label") or self.status_label is None:
            self.status_label = Label(message, classes=log_level)
            self.mount(self.status_label)
        else:
            self.status_label.update(message)
            self.status_label.set_classes(log_level)

    def reload_config(self, config_path: str = None) -> None:
        if config_path:
            self.config_path = config_path
        if self.dfs and self.top_kernel:
            self.update_results(self.dfs, self.top_kernel)

    def build_header(self):
        for kernel in self.top_kernel:
            self.keys.update(kernel.keys())

        self.keys = sorted(self.keys)

        if "Kernel_Name" in self.keys:
            self.keys.remove("Kernel_Name")
            self.keys.insert(0, "Kernel_Name")

        header_text = " | ".join(f"{key:25}" for key in self.keys)
        header_label = Label(header_text, classes="kernel-table-header")

        return header_label

    def build_selector(self):
        radio_buttons = []

        for i, kernel in enumerate(self.top_kernel):
            row_data = []
            for key in self.keys:
                value = str(kernel.get(key, "N/A"))
                if len(value) > 18:
                    value = value[:15] + "..."
                row_data.append(f"{value:25}")

            row_text = " | ".join(row_data)
            radio_button = RadioButton(row_text, id=f"kernel-{i}")
            radio_button.kernel_data = kernel
            radio_buttons.append(radio_button)

        selector = RadioSet(*radio_buttons)

        return selector

    @on(RadioSet.Changed)
    def on_radio_changed(self, event: RadioSet.Changed) -> None:
        if not event.pressed:
            return

        kernel_data = getattr(event.pressed, "kernel_data", None)
        if kernel_data and "Kernel_Name" in kernel_data:
            self.current_selection = kernel_data["Kernel_Name"]
            self.update_bottom_content()

    def update_bottom_content(self):
        bottom_container = self.query_one("#bottom-container", VerticalScroll)
        bottom_container.remove_children()

        bottom_container.mount(
            Label("Toggle kernel selection to view detailed analysis.")
        )

        if not (self.current_selection and self.current_selection in self.dfs):
            bottom_container.mount(
                Label(
                    f"No data available for kernel: {self.current_selection}",
                    classes="error",
                )
            )
            return

        bottom_container.mount(
            Label(f"Current kernel selection: {self.current_selection}")
        )

        try:
            sections = build_all_sections(
                self.dfs[self.current_selection], self.config_path
            )
            for section in sections:
                bottom_container.mount(section)
        except Exception as e:
            bottom_container.mount(
                Label(f"Error displaying results: {str(e)}", classes="error")
            )

    def _get_sorted_keys(self):
        keys = set()
        for kernel in self.top_kernel:
            keys.update(kernel.keys())

        keys = sorted(keys)
        if "Kernel_Name" in keys:
            keys.remove("Kernel_Name")
            keys.insert(0, "Kernel_Name")

        return keys
