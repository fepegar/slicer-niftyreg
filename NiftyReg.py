import os
import time
import shutil
import random
import string
import datetime
import subprocess
import collections

import numpy as np
import sitkUtils as su
import SimpleITK as sitk
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

NIFTYREG_LINK = 'http://cmictig.cs.ucl.ac.uk/wiki/index.php/NiftyReg'
ALADIN_PATH = os.path.expanduser('~/bin/reg_aladin')
F3D_PATH = os.path.expanduser('~/bin/reg_f3d')
TRANSFORMATIONS_MAP = collections.OrderedDict([('Rigid', ALADIN_PATH),
                                               ('Affine', ALADIN_PATH),
                                               ('Non-linear', F3D_PATH)])


class NiftyReg(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "NiftyReg"
        self.parent.categories = ["Registration"]
        self.parent.dependencies = []
        self.parent.contributors = ["Fernando Perez-Garcia (fepegar@gmail.com - Brain & Spine Institute - Paris)"]
        self.parent.helpText = """NiftyReg is an open-source software for efficient medical image registration."""
        self.parent.acknowledgementText = """NiftyReg is developed and maintained by Marc Modat (University College London)."""



class NiftyRegWidget(ScriptedLoadableModuleWidget):

    def __init__(self, parent):

        ScriptedLoadableModuleWidget.__init__(self, parent)


    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = NiftyRegLogic()
        self.makeGUI()
        self.onTransformationTypeChanged()
        self.onInputModified()


    def makeGUI(self):
        """
        [reg_aladin] Usage:	reg_aladin -ref <filename> -flo <filename> [OPTIONS].
        [reg_aladin] 	-ref <filename>	Reference image filename (also called Target or Fixed) (mandatory)
        [reg_aladin] 	-flo <filename>	Floating image filename (also called Source or moving) (mandatory)
        [reg_aladin]
        [reg_aladin] * * OPTIONS * *
        [reg_aladin] 	-noSym 			The symmetric version of the algorithm is used by default. Use this flag to disable it.
        [reg_aladin] 	-rigOnly		To perform a rigid registration only. (Rigid+affine by default)
        [reg_aladin] 	-affDirect		Directly optimize 12 DoF affine. (Default is rigid initially then affine)
        [reg_aladin] 	-aff <filename>		Filename which contains the output affine transformation. [outputAffine.txt]
        [reg_aladin] 	-inaff <filename>	Filename which contains an input affine transformation. (Affine*Reference=Floating) [none]
        [reg_aladin] 	-rmask <filename>	Filename of a mask image in the reference space.
        [reg_aladin] 	-fmask <filename>	Filename of a mask image in the floating space. (Only used when symmetric turned on)
        [reg_aladin] 	-res <filename>		Filename of the resampled image. [outputResult.nii]
        [reg_aladin] 	-maxit <int>		Maximal number of iterations of the trimmed least square approach to perform per level. [5]
        [reg_aladin] 	-ln <int>		Number of levels to use to generate the pyramids for the coarse-to-fine approach. [3]
        [reg_aladin] 	-lp <int>		Number of levels to use to run the registration once the pyramids have been created. [ln]
        [reg_aladin] 	-smooR <float>		Standard deviation in mm (voxel if negative) of the Gaussian kernel used to smooth the Reference image. [0]
        [reg_aladin] 	-smooF <float>		Standard deviation in mm (voxel if negative) of the Gaussian kernel used to smooth the Floating image. [0]
        [reg_aladin] 	-refLowThr <float>	Lower threshold value applied to the reference image. [0]
        [reg_aladin] 	-refUpThr <float>	Upper threshold value applied to the reference image. [0]
        [reg_aladin] 	-floLowThr <float>	Lower threshold value applied to the floating image. [0]
        [reg_aladin] 	-floUpThr <float>	Upper threshold value applied to the floating image. [0]
        [reg_aladin] 	-nac			Use the nifti header origin to initialise the transformation. (Image centres are used by default)
        [reg_aladin] 	-cog			Use the input masks centre of mass to initialise the transformation. (Image centres are used by default)
        [reg_aladin] 	-interp			Interpolation order to use internally to warp the floating image.
        [reg_aladin] 	-iso			Make floating and reference images isotropic if required.
        [reg_aladin] 	-pv <int>		Percentage of blocks to use in the optimisation scheme. [50]
        [reg_aladin] 	-pi <int>		Percentage of blocks to consider as inlier in the optimisation scheme. [50]
        [reg_aladin] 	-speeeeed		Go faster
        [reg_aladin] 	-voff			Turns verbose off [on]
        """

        self.makeInputsButton()
        self.makeParametersButton()
        self.makeOutputsButton()

        self.applyButton = qt.QPushButton('Apply')
        self.applyButton.setDisabled(True)
        self.applyButton.clicked.connect(self.onApply)
        self.parent.layout().addWidget(self.applyButton)

        self.parent.layout().addStretch()


    def makeInputsButton(self):
        self.inputsCollapsibleButton = ctk.ctkCollapsibleButton()
        self.inputsCollapsibleButton.text = 'Inputs'
        self.layout.addWidget(self.inputsCollapsibleButton)

        self.inputsLayout = qt.QFormLayout(self.inputsCollapsibleButton)

        # Reference
        self.referenceSelector = slicer.qMRMLNodeComboBox()
        self.referenceSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.referenceSelector.selectNodeUponCreation = False
        self.referenceSelector.addEnabled = False
        self.referenceSelector.removeEnabled = True
        self.referenceSelector.noneEnabled = False
        self.referenceSelector.showHidden = False
        self.referenceSelector.showChildNodeTypes = True
        self.referenceSelector.setMRMLScene(slicer.mrmlScene)
        self.referenceSelector.currentNodeChanged.connect(self.onInputModified)
        self.inputsLayout.addRow("Reference: ", self.referenceSelector)

        # Floating
        self.floatingSelector = slicer.qMRMLNodeComboBox()
        self.floatingSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.floatingSelector.selectNodeUponCreation = False
        self.floatingSelector.addEnabled = False
        self.floatingSelector.removeEnabled = True
        self.floatingSelector.noneEnabled = False
        self.floatingSelector.showHidden = True
        self.floatingSelector.showChildNodeTypes = True
        self.floatingSelector.setMRMLScene(slicer.mrmlScene)
        self.floatingSelector.currentNodeChanged.connect(self.onInputModified)
        self.inputsLayout.addRow("Floating: ", self.floatingSelector)

        # Initial transform
        self.initialTransformSelector = slicer.qMRMLNodeComboBox()
        self.initialTransformSelector.nodeTypes = ["vtkMRMLTransformNode"]
        self.initialTransformSelector.selectNodeUponCreation = True
        self.initialTransformSelector.addEnabled = False
        self.initialTransformSelector.removeEnabled = True
        self.initialTransformSelector.noneEnabled = True
        self.initialTransformSelector.showHidden = False
        self.initialTransformSelector.showChildNodeTypes = True
        self.initialTransformSelector.setMRMLScene(slicer.mrmlScene)
        self.initialTransformSelector.baseName = 'Initial transform'
        self.initialTransformSelector.currentNodeChanged.connect(self.onInputModified)
        self.inputsLayout.addRow("Initial transform: ", self.initialTransformSelector)


    def makeOutputsButton(self):
        self.outputsCollapsibleButton = ctk.ctkCollapsibleButton()
        self.outputsCollapsibleButton.text = 'Outputs'
        self.layout.addWidget(self.outputsCollapsibleButton)

        self.outputsLayout = qt.QFormLayout(self.outputsCollapsibleButton)

        # Result transform
        self.resultTransformSelector = slicer.qMRMLNodeComboBox()
        self.resultTransformSelector.nodeTypes = ["vtkMRMLTransformNode"]
        self.resultTransformSelector.selectNodeUponCreation = True
        self.resultTransformSelector.addEnabled = True
        self.resultTransformSelector.removeEnabled = True
        self.resultTransformSelector.renameEnabled = True
        self.resultTransformSelector.noneEnabled = True
        self.resultTransformSelector.showHidden = False
        self.resultTransformSelector.showChildNodeTypes = True
        self.resultTransformSelector.setMRMLScene(slicer.mrmlScene)
        self.resultTransformSelector.currentNodeChanged.connect(self.onInputModified)
        self.outputsLayout.addRow("Result transform: ", self.resultTransformSelector)


        # Result volume
        self.resultVolumeSelector = slicer.qMRMLNodeComboBox()
        self.resultVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.resultVolumeSelector.selectNodeUponCreation = True
        self.resultVolumeSelector.addEnabled = True
        self.resultVolumeSelector.removeEnabled = True
        self.resultVolumeSelector.renameEnabled = True
        self.resultVolumeSelector.noneEnabled = True
        self.resultVolumeSelector.showHidden = False
        self.resultVolumeSelector.showChildNodeTypes = True
        self.resultVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.resultVolumeSelector.currentNodeChanged.connect(self.onInputModified)
        self.outputsLayout.addRow("Result volume: ", self.resultVolumeSelector)


    def makeParametersButton(self):
        self.parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        self.parametersCollapsibleButton.text = 'Parameters'
        self.layout.addWidget(self.parametersCollapsibleButton)

        self.parametersLayout = qt.QVBoxLayout(self.parametersCollapsibleButton)
        self.parametersTabWidget = qt.QTabWidget()
        self.parametersLayout.addWidget(self.parametersTabWidget)

        self.makeTransformationTypeWidgets()
        self.makePyramidWidgets()
        self.makeThresholdsWidgets()


    def makeTransformationTypeWidgets(self):
        self.trsfTypeTab = qt.QWidget()
        self.parametersTabWidget.addTab(self.trsfTypeTab, 'Transformation type')
        trsfTypeLayout = qt.QHBoxLayout(self.trsfTypeTab)

        self.trsfTypeRadioButtons = []
        for trsfType in TRANSFORMATIONS_MAP:
            radioButton = qt.QRadioButton(trsfType)
            radioButton.clicked.connect(self.onTransformationTypeChanged)
            self.trsfTypeRadioButtons.append(radioButton)
            trsfTypeLayout.addWidget(radioButton)

        self.trsfTypeRadioButtons[0].setChecked(True)


    def makePyramidWidgets(self):
        self.pyramidTab = qt.QWidget()
        self.parametersTabWidget.addTab(self.pyramidTab, 'Pyramid levels')
        self.pyramidLayout = qt.QGridLayout(self.pyramidTab)

        self.pyramidLayout.addWidget(qt.QLabel('Reference'), 0, 2)
        self.pyramidLayout.addWidget(qt.QLabel('Floating'), 0, 3)

        self.pyramidHighestSpinBox = qt.QSpinBox()
        self.pyramidHighestSpinBox.value = 3
        self.pyramidHighestSpinBox.setAlignment(qt.Qt.AlignCenter)
        self.pyramidHighestSpinBox.valueChanged.connect(self.onPyramidLevelsChanged)
        self.pyramidHighestReferenceLabel = qt.QLabel()
        self.pyramidHighestReferenceLabel.setAlignment(qt.Qt.AlignCenter)
        self.pyramidHighestFloatingLabel = qt.QLabel()
        self.pyramidHighestFloatingLabel.setAlignment(qt.Qt.AlignCenter)
        self.pyramidLayout.addWidget(qt.QLabel('Highest:'), 1, 0)
        self.pyramidLayout.addWidget(self.pyramidHighestSpinBox, 1, 1)
        self.pyramidLayout.addWidget(self.pyramidHighestReferenceLabel, 1, 2)
        self.pyramidLayout.addWidget(self.pyramidHighestFloatingLabel, 1, 3)

        self.pyramidLowestSpinBox = qt.QSpinBox()
        self.pyramidLowestSpinBox.value = 2
        self.pyramidLowestSpinBox.setAlignment(qt.Qt.AlignCenter)
        self.pyramidLowestSpinBox.valueChanged.connect(self.onPyramidLevelsChanged)
        self.pyramidLowestReferenceLabel = qt.QLabel()
        self.pyramidLowestReferenceLabel.setAlignment(qt.Qt.AlignCenter)
        self.pyramidLowestFloatingLabel = qt.QLabel()
        self.pyramidLowestFloatingLabel.setAlignment(qt.Qt.AlignCenter)
        self.pyramidLayout.addWidget(qt.QLabel('Lowest:'), 2, 0)
        self.pyramidLayout.addWidget(self.pyramidLowestSpinBox, 2, 1)
        self.pyramidLayout.addWidget(self.pyramidLowestReferenceLabel, 2, 2)
        self.pyramidLayout.addWidget(self.pyramidLowestFloatingLabel, 2, 3)


    def makeThresholdsWidgets(self):
        self.thresholdsTab = qt.QWidget()
        self.parametersTabWidget.addTab(self.thresholdsTab, 'Thresholds')
        self.thresholdsLayout = qt.QFormLayout(self.thresholdsTab)

        self.referenceThresholdSlider = ctk.ctkRangeWidget()
        self.referenceThresholdSlider.decimals = 0
        self.referenceThresholdSlider.valuesChanged.connect(self.onReferenceThresholdSlider)
        self.thresholdsLayout.addRow('Reference: ', self.referenceThresholdSlider)

        self.floatingThresholdSlider = ctk.ctkRangeWidget()
        self.floatingThresholdSlider.decimals = 0
        self.floatingThresholdSlider.valuesChanged.connect(self.onFloatingThresholdSlider)
        self.thresholdsLayout.addRow('Floating: ', self.floatingThresholdSlider)


    def getSelectedTransformationType(self):
        for b in self.trsfTypeRadioButtons:
            if b.isChecked():
                trsfType = str(b.text)
        return trsfType


    def readParameters(self):
        self.referenceVolumeNode = self.referenceSelector.currentNode()
        self.floatingVolumeNode = self.floatingSelector.currentNode()
        self.initialTransformNode = self.initialTransformSelector.currentNode()

        self.resultVolumeNode = self.resultVolumeSelector.currentNode()
        self.resultTransformNode = self.resultTransformSelector.currentNode()

        self.referenceThresholds = self.logic.getThresholdRange(self.referenceVolumeNode)
        self.floatingThresholds = self.logic.getThresholdRange(self.floatingVolumeNode)


    def getCommandLineList(self):
        self.tempDir = str(slicer.util.tempDirectory())

        self.refPath = self.logic.getNodeFilepath(self.referenceVolumeNode)
        self.floPath = self.logic.getNodeFilepath(self.floatingVolumeNode)

        refName = self.referenceVolumeNode.GetName()
        floName = self.floatingVolumeNode.GetName()

        dateTime = datetime.datetime.now()

        # We make sure they are in the disk
        if not self.refPath or not self.logic.hasNiftiExtension(self.refPath):
            self.refPath = self.logic.getTempPath(self.tempDir,
                                                  '.nii',
                                                  filename=refName,
                                                  dateTime=dateTime)
            slicer.util.saveNode(self.referenceVolumeNode, self.refPath)

        if not self.floPath or not self.logic.hasNiftiExtension(self.floPath):
            self.floPath = self.logic.getTempPath(self.tempDir,
                                                  '.nii',
                                                  filename=floName,
                                                  dateTime=dateTime)
            slicer.util.saveNode(self.floatingVolumeNode, self.floPath)


        self.resPath = self.logic.getTempPath(self.tempDir,
                                              '.nii',
                                              filename='{}_on_{}'.format(floName, refName),
                                              dateTime=dateTime)

        trsfType = self.getSelectedTransformationType()
        binaryPath = TRANSFORMATIONS_MAP[trsfType]

        if binaryPath == ALADIN_PATH:
            extension = '.txt'
        elif binaryPath == F3D_PATH:
            extension = '.nii'
        self.resultTransformPath = self.logic.getTempPath(self.tempDir,
                                                          extension,
                                                          filename='t_ref-{}_flo-{}'.format(refName, floName),
                                                          dateTime=dateTime)



        # Save the command line for debugging
        self.cmdPath = self.logic.getTempPath(self.tempDir,
                                              '.txt',
                                              filename='cmd_ref-{}_flo-{}_{}'.format(refName, floName, trsfType),
                                              dateTime=dateTime)

        self.logPath = self.logic.getTempPath(self.tempDir,
                                              '.txt',
                                              filename='log_ref-{}_flo-{}_{}'.format(refName, floName, trsfType),
                                              dateTime=dateTime)

        refThreshMin, refThreshMax = self.referenceThresholds
        floThreshMin, floThreshMax = self.floatingThresholds

        ln, lp = self.getPyramidLevels()

        cmd = [binaryPath]
        cmd += ['-ref', self.refPath]
        cmd += ['-flo', self.floPath]
        cmd += ['-res', self.resPath]
        if binaryPath == ALADIN_PATH:
            if trsfType == 'Rigid':
                cmd += ['-rigOnly']
            elif trsfType == 'Affine':
                cmd += ['-affDirect']
            cmd += ['-aff', self.resultTransformPath]
            cmd += ['-refLowThr', str(refThreshMin)]
            cmd += ['-refUpThr', str(refThreshMax)]
            cmd += ['-floLowThr', str(floThreshMin)]
            cmd += ['-floUpThr', str(floThreshMax)]
        elif binaryPath == F3D_PATH:
            cmd += ['-cpp', self.resultTransformPath]
            cmd += ['-rLwTh', str(refThreshMin)]
            cmd += ['-rUpTh', str(refThreshMax)]
            cmd += ['-fLwTh', str(floThreshMin)]
            cmd += ['-fUpTh', str(floThreshMax)]
        cmd += ['-ln', str(ln)]
        cmd += ['-lp', str(lp)]
        # cmd += ['-transformation-type', trsfType]
        # cmd += ['-command-line', self.cmdPath]
        # cmd += ['-logfile', self.logPath]

        if self.initialTransformNode:
            self.initialTransformPath = str(self.logic.getTempPath(self.tempDir, '.txt', dateTime=dateTime))
            self.logic.writeNiftyRegMatrix(self.initialTransformNode, self.initialTransformPath)
            if binaryPath == ALADIN_PATH:
                cmd += ['-inaff', self.initialTransformPath]
            elif binaryPath == F3D_PATH:
                cmd += ['-aff', self.initialTransformPath]

        self.commandLineList = cmd


    def printCommandLine(self):
        """
        Pretty-prints the command line so that it can be copied from the Python
        console and pasted on a terminal.
        """
        prettyCmd = []
        for s in self.commandLineList:
            if s.startswith('-'):
                prettyCmd.append('\\\n')
            prettyCmd.append(s)
        print(' '.join(prettyCmd))


    def repareResults(self):
        """
        This is used to convert output .hdr Analyze into NIfTI
        """

        if self.resPath.endswith('.hdr'):
            print('Correcting result .hdr image')
            shutil.copy(self.refPath, self.resPath)


    def loadResults(self):
        # Remove transform from reference
        self.referenceVolumeNode.SetAndObserveTransformNodeID(None)

        # Load the result node
        if self.resultVolumeNode is not None:
            # Remove result node
            resultName = self.resultVolumeNode.GetName()
            slicer.mrmlScene.RemoveNode(self.resultVolumeNode)

            # Load the new one
            # When loading a 2D image with slicer.util, there is a bug that
            # keeps stacking the output result instead of creating a 2D image
            if self.logic.is2D(self.referenceVolumeNode):  # load using SimpleITK
                resultImage = sitk.ReadImage(self.resPath)
                su.PushToSlicer(resultImage, resultName, overwrite=True)
                self.resultVolumeNode = slicer.util.getNode(resultName)
            else:  # load using slicer.util.loadVolume()
                self.resultVolumeNode = slicer.util.loadVolume(self.resPath, returnNode=True)[1]
            self.resultVolumeNode.SetName(resultName)
            self.resultVolumeSelector.setCurrentNode(self.resultVolumeNode)
            fgVolume = self.resultVolumeNode

        # If a transform was given, copy the result in it and apply it to the floating image
        trsfType = self.getSelectedTransformationType()

        if self.resultTransformNode is not None:
            if trsfType != 'Non-linear':  # linear
                matrix = self.logic.readNiftyRegMatrix(self.resultTransformPath)
                vtkMatrix = self.logic.getVTKMatrixFromNumpyMatrix(matrix)
                self.resultTransformNode.SetMatrixTransformFromParent(vtkMatrix)
            else:  # non-linear
                # Remove result transform node from scene
                resultTransformName = self.resultTransformNode.GetName()
                slicer.mrmlScene.RemoveNode(self.resultTransformNode)

                # Load the generated transform node
                self.displacementFieldPath = self.resultTransformPath
                self.resultTransformNode = self.logic.vectorfieldToDisplacementField(
                    self.resultTransformPath,
                    self.referenceVolumeNode,
                    self.displacementFieldPath)
                self.resultTransformNode.SetName(resultTransformName)
                self.resultTransformSelector.setCurrentNode(self.resultTransformNode)

            # Apply transform to floating if no result volume node was selected
            if self.resultVolumeNode is None:
                self.floatingVolumeNode.SetAndObserveTransformNodeID(self.resultTransformNode.GetID())
                fgVolume = self.floatingVolumeNode

        self.logic.setSlicesBackAndForeground(bgVolume=self.referenceVolumeNode,
                                              fgVolume=fgVolume,
                                              opacity=0.5,
                                              colors=True)

        self.logic.centerViews()


    def outputsExist(self):
        """
        We need this because it's not clear that blockmatching returns non-zero
        when failed
        """
        if self.resultVolumeNode is not None:
            if not os.path.isfile(self.resPath):
                return False

        if self.resultTransformNode is not None:
            if not os.path.isfile(self.resultTransformPath):
                return False

        return True


    def validateMatrices(self):
        refQFormCode, refSFormCode = self.logic.getQFormAndSFormCodes(self.referenceVolumeNode)
        floQFormCode, floSFormCode = self.logic.getQFormAndSFormCodes(self.floatingVolumeNode)
        validCodes = 1, 2, 3
        if refQFormCode != 0 and floQFormCode != 0: return

        messages = ['Registration results might be unexpected:', '\n']
        if refQFormCode not in validCodes:
            messages.append('Reference image does not have a valid qform_code: {}'.format(refQFormCode))
        if floQFormCode not in validCodes:
            messages.append('Floating image does not have a valid qform_code: {}'.format(floQFormCode))
        message = '\n'.join(messages)
        slicer.util.warningDisplay(message)


    def validateRefIsFloating(self):
        if self.referenceVolumeNode is self.floatingVolumeNode:
            slicer.util.warningDisplay('Reference and floating images are the same')


    def validateDataTypes(self):
        refDouble = self.logic.isDouble(self.referenceVolumeNode)
        floDouble = self.logic.isDouble(self.floatingVolumeNode)

        if not refDouble and not floDouble:
            return True

        messages = ['Data type not handled yet:', '\n']
        if refDouble:
            messages.append('Reference image does not have a valid data type')
        if floDouble:
            messages.append('Floating image does not have a valid data type')
        message = '\n'.join(messages)
        slicer.util.errorDisplay(message)
        return False


    def validateParameters(self):
        validDataTypes = self.validateDataTypes()
        self.validateRefIsFloating()
        self.validateMatrices()

        return validDataTypes


    ### Signals ###
    def onInputModified(self):
        self.readParameters()

        # Enable apply button
        validMinimumInputs = self.referenceVolumeNode and \
                             self.floatingVolumeNode and \
                             (self.resultVolumeNode or self.resultTransformNode)
        self.applyButton.setEnabled(validMinimumInputs)

        # Update pyramid widgets
        self.referencePyramidMap = self.logic.getPyramidShapesMap(self.referenceVolumeNode)
        self.floatingPyramidMap = self.logic.getPyramidShapesMap(self.floatingVolumeNode)

        if self.referencePyramidMap is None:
            self.pyramidHighestSpinBox.setDisabled(True)
            self.pyramidLowestSpinBox.setDisabled(True)
        else:
            self.pyramidHighestSpinBox.setEnabled(True)
            self.pyramidLowestSpinBox.setEnabled(True)
            self.pyramidHighestSpinBox.maximum = max(self.referencePyramidMap.keys())
        self.onPyramidLevelsChanged()

        # Update thresholds sliders
        if self.referenceVolumeNode is None:
            self.referenceThresholdSlider.setDisabled(True)
        else:
            minValue, maxValue = self.logic.getRange(self.referenceVolumeNode)
            self.referenceThresholdSlider.minimum = minValue
            self.referenceThresholdSlider.maximum = maxValue
            thresholdMin, thresholdMax = self.logic.getThresholdRange(self.referenceVolumeNode)
            self.referenceThresholdSlider.minimumValue = thresholdMin
            self.referenceThresholdSlider.maximumValue = thresholdMax
            self.referenceThresholdSlider.setEnabled(True)

        if self.floatingVolumeNode is None:
            self.floatingThresholdSlider.setDisabled(True)
        else:
            minValue, maxValue = self.logic.getRange(self.floatingVolumeNode)
            self.floatingThresholdSlider.minimum = minValue
            self.floatingThresholdSlider.maximum = maxValue
            thresholdMin, thresholdMax = self.logic.getThresholdRange(self.floatingVolumeNode)
            self.floatingThresholdSlider.minimumValue = thresholdMin
            self.floatingThresholdSlider.maximumValue = thresholdMax
            self.floatingThresholdSlider.setEnabled(True)


    def onTransformationTypeChanged(self):
        trsf = self.getSelectedTransformationType()
        self.resultTransformSelector.baseName = 'Output %s transform' % trsf
        self.resultVolumeSelector.baseName = 'Output %s volume' % trsf


    def onPyramidLevelsChanged(self):

        def getShapeString(shape):
            return ' x '.join([str(n) for n in shape])

        self.pyramidLowestSpinBox.maximum = self.pyramidHighestSpinBox.value
        self.pyramidHighestSpinBox.minimum = self.pyramidLowestSpinBox.value

        if self.referencePyramidMap is None:
            self.pyramidHighestLabel.text = ''
            self.pyramidLowestLabel.text = ''
        else:
            highestLevelShape = self.referencePyramidMap[self.pyramidHighestSpinBox.value]
            lowestLevelShape = self.referencePyramidMap[self.pyramidLowestSpinBox.value]
            self.pyramidHighestReferenceLabel.text = getShapeString(highestLevelShape)
            self.pyramidLowestReferenceLabel.text = getShapeString(lowestLevelShape)

            highestLevelShape = self.floatingPyramidMap[self.pyramidHighestSpinBox.value]
            lowestLevelShape = self.floatingPyramidMap[self.pyramidLowestSpinBox.value]
            self.pyramidHighestFloatingLabel.text = getShapeString(highestLevelShape)
            self.pyramidLowestFloatingLabel.text = getShapeString(lowestLevelShape)


    def onReferenceThresholdSlider(self):
        if self.referenceVolumeNode is not None:
            displayNode = self.referenceVolumeNode.GetDisplayNode()
            displayNode.AutoThresholdOff()
            displayNode.ApplyThresholdOn()
            thresMin = self.referenceThresholdSlider.minimumValue
            thresMax = self.referenceThresholdSlider.maximumValue
            displayNode.SetThreshold(thresMin, thresMax)


    def onFloatingThresholdSlider(self):
        if self.floatingVolumeNode is not None:
            displayNode = self.floatingVolumeNode.GetDisplayNode()
            displayNode.AutoThresholdOff()
            displayNode.ApplyThresholdOn()
            thresMin = self.floatingThresholdSlider.minimumValue
            thresMax = self.floatingThresholdSlider.maximumValue
            displayNode.SetThreshold(thresMin, thresMax)


    def onApply(self):
        self.readParameters()
        self.getCommandLineList()
        if not self.validateParameters(): return
        print('\n\n')
        self.printCommandLine()
        tIni = time.time()
        try:
            qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
            p = subprocess.Popen(self.commandLineList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.communicate()
            print('\nBlockmatching returned {}'.format(p.returncode))
            if p.returncode != 0 or not self.outputsExist():
                # Newer versions of blockmatching return 0
                # Apparently it always returns 0 :(
                qt.QApplication.restoreOverrideCursor()
                errorMessage = ''
                if not self.outputsExist():
                    errorMessage += 'Output volume not written on the disk\n\n'
                errorMessage += output[1]
                slicer.util.errorDisplay(errorMessage, windowTitle="Registration error")
            else:
                tFin = time.time()
                print('\nRegistration completed in {:.2f} seconds'.format(tFin - tIni))
                self.repareResults()
                self.loadResults()
        except OSError as e:
            print(e)
            print('Is blockmatching correctly installed?')
        finally:
            qt.QApplication.restoreOverrideCursor()



class NiftyRegLogic(ScriptedLoadableModuleLogic):

    def getNodeFilepath(self, node):
        storageNode = node.GetStorageNode()
        if storageNode is None:
            return None
        else:
            return storageNode.GetFileName()


    def getTempPath(self, directory, ext, length=10, filename=None, dateTime=None):
        if filename is None:
            filename = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
        filename = filename.replace(' ', '_')  # avoid errors when running a command with spaces
        filename += ext
        if dateTime is not None:
            filename = '{}_{}'.format(dateTime.strftime("%Y%m%d_%H%M%S"), filename)
        return os.path.join(directory, filename)


    def centerViews(self):
        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()

        for color in 'Red', 'Yellow', 'Green':
            sliceLogic = slicer.app.layoutManager().sliceWidget(color).sliceLogic()
            sliceLogic.FitSliceToAll()


    def setSlicesBackAndForeground(self, bgVolume=None, fgVolume=None, opacity=None, colors=False, link=True):
        for color in 'Red', 'Yellow', 'Green':
            sliceLogic = slicer.app.layoutManager().sliceWidget(color).sliceLogic()
            compositeNode = sliceLogic.GetSliceCompositeNode()
            if fgVolume:
                compositeNode.SetForegroundVolumeID(fgVolume.GetID())
            if bgVolume:
                compositeNode.SetBackgroundVolumeID(bgVolume.GetID())
            if opacity is not None:
                compositeNode.SetForegroundOpacity(opacity)
            if link:
                compositeNode.SetLinkedControl(True)

        if colors:
            GREEN = 'vtkMRMLColorTableNodeGreen'
            MAGENTA = 'vtkMRMLColorTableNodeMagenta'

            bgImageDisplayNode = slicer.util.getNode(compositeNode.GetBackgroundVolumeID()).GetDisplayNode()
            fgImageDisplayNode = slicer.util.getNode(compositeNode.GetForegroundVolumeID()).GetDisplayNode()

            compositeNode.SetForegroundOpacity(.5)
            bgImageDisplayNode.SetAndObserveColorNodeID(GREEN)
            fgImageDisplayNode.SetAndObserveColorNodeID(MAGENTA)


    def getNumpyMatrixFromVTKMatrix(self, vtkMatrix):
        matrix = np.identity(4, np.float)
        for row in range(4):
            for col in range(4):
                matrix[row,col] = vtkMatrix.GetElement(row,col)
        return matrix


    def getVTKMatrixFromNumpyMatrix(self, numpyMatrix):
        dimensions = len(numpyMatrix) - 1
        if dimensions == 2:
            vtkMatrix = vtk.vtkMatrix3x3()
        elif dimensions == 3:
            vtkMatrix = vtk.vtkMatrix4x4()
        else:
            raise ValueError('Unknown matrix dimensions.')

        for row in range(dimensions + 1):
            for col in range(dimensions + 1):
                vtkMatrix.SetElement(row, col, numpyMatrix[row,col])
        return vtkMatrix


    def readNiftyRegMatrix(self, trsfPath):
        with open(trsfPath) as f:
            return np.loadtxt(f.readlines())


    def writeNiftyRegMatrix(self, transformNode, trsfPath):
        vtkMatrix = vtk.vtkMatrix4x4()
        transformNode.GetMatrixTransformFromParent(vtkMatrix)
        matrix = self.getNumpyMatrixFromVTKMatrix(vtkMatrix)
        lines = []
        for row in matrix:
            line = []
            for n in row:
                line.append('{:13.8f}'.format(n))
            lines.append(''.join(line))
        line = '\n'.join(lines)
        with open(trsfPath, 'w') as f:
            f.write(line)


    def vectorfieldToDisplacementField(self, vectorfieldPath, referenceNode, displacementFieldPath):
        stream = self.getDataStreamFromVectorField(vectorfieldPath)
        referenceImage = su.PullFromSlicer(referenceNode.GetID())
        shape = list(referenceImage.GetSize())
        shape.reverse()

        # Example of 2D shape at this point: [1, 540, 940]

        # Blockmatching output might be 2D
        is2D = shape[0] == 1
        componentsPerVector = 2 if is2D else 3
        shape.append(componentsPerVector)
        reshaped = stream.reshape(shape)

        # Force the output to be 3D
        if is2D:
            zeros = np.zeros_like(reshaped[..., :1])  # z component of the vectors
            reshaped = np.concatenate((reshaped, zeros), axis=3)

        reshaped[..., :2] *= -1  # RAS to LPS
        displacementImage = sitk.GetImageFromArray(reshaped)
        displacementImage.SetOrigin(referenceImage.GetOrigin())
        displacementImage.SetDirection(referenceImage.GetDirection())
        displacementImage.SetSpacing(referenceImage.GetSpacing())

        # TODO: convert the image directly into a transform to save space and time
        sitk.WriteImage(displacementImage, displacementFieldPath)
        transformNode = slicer.util.loadTransform(displacementFieldPath, returnNode=True)[1]
        return transformNode


    def getDataStreamFromVectorField(self, vectorfieldPath):
        HEADER_SIZE = 256
        with open(vectorfieldPath, mode='rb') as f:  # b is important -> binary
            f.seek(HEADER_SIZE)
            imageData = f.read()
        imageData = np.fromstring(imageData, dtype=np.float32)
        return imageData


    def getNIFTIHeader(self, volumeNode):
        reader = vtk.vtkNIFTIImageReader()
        filepath = self.getNodeFilepath(volumeNode)
        reader.SetFileName(filepath)
        reader.Update()
        header = reader.GetNIFTIHeader()
        return header


    def getQFormAndSFormCodes(self, volumeNode):
        header = self.getNIFTIHeader(volumeNode)
        qform_code = header.GetQFormCode()
        sform_code = header.GetSFormCode()
        return qform_code, sform_code


    def getPyramidShapesMap(self, volumeNode):

        def halve(shape):
            return [int(round(float(n)/2)) for n in shape]

        if volumeNode is None: return None

        imageData = volumeNode.GetImageData()
        shape = list(imageData.GetDimensions())

        level = 0
        shapesMap = {level: shape}

        lastLevel = False
        while not lastLevel:
            oldShape = shapesMap[level]
            newShape = halve(oldShape)
            level += 1

            if min(newShape) < 32:
                lastLevel = True
            else:
                shapesMap[level] = newShape

        return shapesMap


    def hasNiftiExtension(self, path):
        for ext in '.hdr', '.img', '.img.gz', '.nii', '.nii.gz':
            if path.endswith(ext):
                return True
        return False


    def is2D(self, volumeNode):
        if volumeNode is None: return
        imageData = volumeNode.GetImageData()
        if imageData is None: return
        dimensions = imageData.GetDimensions()
        thirdDimension = dimensions[2]
        is2D = thirdDimension == 1
        return is2D


    def isDouble(self, volumeNode):
        header = self.getNIFTIHeader(volumeNode)
        return header.GetDataType() == 64


    def getRange(self, volumeNode):
        if volumeNode is None: return None
        array = slicer.util.array(volumeNode.GetID())
        return array.min(), array.max()


    def getThresholdRange(self, volumeNode):
        if volumeNode is None: return None
        displayNode = volumeNode.GetDisplayNode()
        return displayNode.GetLowerThreshold(), displayNode.GetUpperThreshold()
