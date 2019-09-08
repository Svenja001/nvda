# brailleViewer.py
# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2014-2017 NV Access Limited
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
from typing import Optional, List

import gui
from logHandler import log
import extensionPoints
from .brailleViewerGui import BrailleViewerFrame

"""
### Overview
This package contains the components for a "Braille Viewer". A window, that shows the braille dots that
would be displayed on a hardware device. The raw text for each cell is also shown.
This tool consists of:
- A GUI for the viewer.
- Construction / destruction / update helpers.

The current intention is to be able to support a physical braille device while using the "Braille Viewer".
Due to limitations in the design of brailleHandler, the number of cells in the "Braille Viewer" must match any
connected physical device.

### Life-cycle
- Constructing / showing the BrailleViewer
	- On startup via L{core.doStartupDialogs}
	- Via NVDA (tools) menu via L{Mainframe.onToggleSpeechViewerCommand}
- Hiding / destroying the BrailleViewer
	- On exit of NVDA.
	- Via NVDA (tools) menu via L{Mainframe.onToggleSpeechViewerCommand}
	- When the Window receives a close event. This means the GUI must be able to call-back to clean up
	BrailleHandler and the NVDA tools menu. This callback happens via the L{postBrailleViewerToolToggledAction}

### Number of cells shown
The default (40) is set in L{createBrailleViewerTool}.

### Routing
Currently not supported.
In order to support routing the user must be able to click on the cells. This means that the BrailleViewer
window gains focus, and the braille values are changed. To avoid this would require substantial changes to
brailleHandler.

### Scrolling
Scrolling is supported by binding a gesture to the braille_scroll_forward and braille scroll_back commands.
For the same reason that Routing is not supported, scrolling via button clicks on the braille viewer window
is not supported.

"""

# global braille viewer driver:
_brailleGui: Optional[BrailleViewerFrame] = None

# Extension points action:
# Triggered every time the Braille Viewer is created / shown or hidden / destroyed.
# Callback definition: Callable(created: bool) -> None
#   created - True for created/shown, False for hidden/destructed.
postBrailleViewerToolToggledAction = extensionPoints.Action()
# Devices with 40 cells are quite common.
DEFAULT_NUM_CELLS = 40


def isBrailleViewerActive() -> bool:
	return bool(_brailleGui)


def update(cells: List[int], rawText: str):
	if _brailleGui:
		_brailleGui.updateBrailleDisplayed(cells, rawText)

def _destroyGUI():
	global _brailleGui
	d: Optional[BrailleViewerFrame] = _brailleGui
	_brailleGui = None
	if d and not d.isDestroyed:
		d.savePositionInformation()
		d.doDestroy()


def destroyBrailleViewer():
	_destroyGUI()
	postBrailleViewerToolToggledAction.notify(created=False)


def _onGuiDestroyed():
	global _brailleGui
	if _brailleGui:  # If True, this wasn't initiated from L{_destroyGUI}
		destroyBrailleViewer()


def createBrailleViewerTool():
	if not gui.mainFrame:
		raise RuntimeError("Can not initialise the BrailleViewerGui: gui.mainFrame not yet initialised")

	import braille  # imported late to avoid a circular import.
	if not braille.handler:
		raise RuntimeError("Can not initialise the BrailleViewerGui: braille.handler not yet initialised")

	numCells = DEFAULT_NUM_CELLS
	if braille.handler.displaySize:
		numCells = braille.handler.displaySize

	global _brailleGui
	if _brailleGui:
		_destroyGUI()
	_brailleGui = BrailleViewerFrame(numCells, _onGuiDestroyed)

	postBrailleViewerToolToggledAction.notify(created=True)

