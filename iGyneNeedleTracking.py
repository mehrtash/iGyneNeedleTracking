from __future__ import division
from __main__ import vtk, qt, ctk, slicer
import numpy, random
#
# iGyne Needle Tracking 
#

class iGyneNeedleTracking:
  def __init__(self, parent):
    import string
    parent.title = "Neddle Tracking"
    parent.categories = ["Gyne IGT"]
    parent.contributors = ["Alireza Mehrtash","Guillaume Pernelle","Xiaojun Chen","Yi Gao","Tina Kapur", "Jan Egger", "Carolina Vale"]
    parent.helpText = string.Template("""  """)
    parent.acknowledgementText = """
     """
    self.parent = parent

#
# qSlicerPythonModuleWidget
#

class iGyneNeedleTrackingWidget:
  def __init__(self, parent=None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

  # Module Variables
    self.timer = qt.QTimer()
    self.timer.setInterval(20)
    self.timer.connect('timeout()', self.doSomething)
    self.fiducialMatrixStatus = False
    self.outsideSign = 0
    self.needleInsertionStarted = False 
    self.dataBufferIsEmpty = True
    self.trajectoryRawData = [ 0, 0, 0] 
    self.minimumDistanceBetweenSeperatePoints = 2 
    #self.n = 48
    #self.p = numpy.zeros((self.n,3))

    # 10 mm offset for template widt
    self.templateWidth = -10   

  def setup(self):
    # Start tracking colllapsible button
    startTrackingCollapsibleButton = ctk.ctkCollapsibleButton()
    startTrackingCollapsibleButton.text = "Gynecological Brachytherapy IGT"
    self.layout.addWidget(startTrackingCollapsibleButton)
    
    # Layout within the tracking settings collapsible button
    startTrackingFormLayout = qt.QFormLayout(startTrackingCollapsibleButton)

    # Bold and large font for needle label
    largeFont = qt.QFont()
    largeFont.setBold(True)
    largeFont.setPixelSize(30)
   
    # Template node selector
    templateLabel = qt.QLabel( 'Template:' )
    templateSelector = slicer.qMRMLNodeComboBox()
    templateSelector.toolTip = "Choose the template model"
    templateSelector.nodeTypes = ['vtkMRMLModelNode']
    templateSelector.setMRMLScene(slicer.mrmlScene)
    templateSelector.addEnabled = False
    templateSelector.noneEnabled= True
    templateSelector.removeEnabled= False
    templateSelector.connect('currentNodeChanged(bool)', self.enableOrDisableStartTrackingButton)
    startTrackingFormLayout.addRow( templateLabel, templateSelector)
    #stylusTrackerLabel.setText('a')
    #stylusTrackerLabel.setFont( largeFont )

    # Stylus tracker transform node selector
    stylusTrackerLabel = qt.QLabel( 'Stylus:' )
    stylusTrackerSelector = slicer.qMRMLNodeComboBox()
    stylusTrackerSelector.toolTip = "Choose the followup scan"
    stylusTrackerSelector.nodeTypes = ['vtkMRMLTransformNode']
    stylusTrackerSelector.setMRMLScene(slicer.mrmlScene)
    stylusTrackerSelector.addEnabled = False
    stylusTrackerSelector.noneEnabled= True
    stylusTrackerSelector.removeEnabled= False
    stylusTrackerSelector.connect('currentNodeChanged(bool)', self.enableOrDisableStartTrackingButton)
    startTrackingFormLayout.addRow( stylusTrackerLabel, stylusTrackerSelector )
    #stylusTrackerLabel.setText('a')
    #stylusTrackerLabel.setFont( largeFont )

    # Template Holes fiducials node selector
    inputFiducialsNodeSelector = slicer.qMRMLNodeComboBox()
    inputFiducialsNodeSelector.objectName = 'inputFiducialsNodeSelector'
    inputFiducialsNodeSelector.toolTip = "Select a fiducial list to define control points for the path."
    inputFiducialsNodeSelector.nodeTypes = ['vtkMRMLAnnotationHierarchyNode', 'vtkMRMLFiducialListNode']
    inputFiducialsNodeSelector.noneEnabled = True
    inputFiducialsNodeSelector.addEnabled = False
    inputFiducialsNodeSelector.removeEnabled = False
    inputFiducialsNodeSelector.connect('currentNodeChanged(bool)', self.enableOrDisableStartTrackingButton)
    startTrackingFormLayout.addRow("Template Holes:", inputFiducialsNodeSelector)
    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', 
                        inputFiducialsNodeSelector, 'setMRMLScene(vtkMRMLScene*)')

    # Start Tracking Button
    startTrackingButton = qt.QPushButton("Start Procedure")
    startTrackingButton.toolTip = "Start Tracking."
    startTrackingButton.enabled = False
    startTrackingButton.checkable = True
    startTrackingFormLayout.addRow( startTrackingButton)
    startTrackingButton.connect('toggled(bool)', self.onStartTrackingButtonClicked)

    # DrawNeedle 
    drawNeedleButton = qt.QPushButton(" Record Track")
    drawNeedleButton .toolTip = "Draw Needles"
    drawNeedleButton.enabled = False 
    drawNeedleButton.checkable = False 
    startTrackingFormLayout.addRow( drawNeedleButton )
    drawNeedleButton.connect('clicked()', self.onDrawNeedleButtonClicked)

    # Needle status collapsible button
    needleStatusCollapsibleButton = ctk.ctkCollapsibleButton()
    needleStatusCollapsibleButton.text = "Needle Status"
    self.layout.addWidget(needleStatusCollapsibleButton)

    # Layout withn the needle status collapsible button
    needleStatusFormLayout = qt.QFormLayout(needleStatusCollapsibleButton)
 
    # Needle Status QLine 
    needleInOutLabel= qt.QLabel('Out')
    #status.setMaxLength(2)
    needleStatusFormLayout.addRow('Needle Status: ', needleInOutLabel)

  # Error Status QLine 
    errorStatus = qt.QLabel('N/A')
    #errorStatus.text="0.00"
    needleStatusFormLayout.addRow('Registration Error:', errorStatus)

  # Needle Status QLine 
    status = qt.QLabel('')
    status.setText('N/A')
    #status.setMaxLength(2)
    status.setFont(largeFont)
    needleStatusFormLayout.addRow(status)
    
    # Slicer MRML and Slicer annotation module
    self.scene = slicer.mrmlScene
    self.logic = slicer.modules.annotations.logic()
    
    # Set local var as instance attribute
    self.templateSelector = templateSelector
    self.stylusTrackerSelector = stylusTrackerSelector
    self.inputFiducialsNodeSelector = inputFiducialsNodeSelector 
    self.startTrackingButton = startTrackingButton
    self.drawNeedleButton = drawNeedleButton
    self.needleInOutLabel= needleInOutLabel 
    self.errorStatus= errorStatus
    self.status= status

  def enableOrDisableStartTrackingButton(self):
    """Connected to both the stylus tracker and input fiducial node selector. It allows to 
    enable or disable the 'start procedure' button."""

    self.startTrackingButton.enabled = self.stylusTrackerSelector.currentNode() != None and self.inputFiducialsNodeSelector.currentNode() != None 

  def onStartTrackingButtonClicked(self,checked):
    """Connected to 'start procedure' button. It allows to:
      - 
      - """
    # Add the transform Node displacements
    # fiducials are two slow! When I put the fiducials under the transform the system was awfully slow!!!!
      
    if self.fiducialMatrixStatus == False:
      self.createFiducialMatrix()
   
    # start timer and perform the funcion doSomething
    if checked:
      self.timer.start()
      self.startTrackingButton.text = "Stop"
    else:
      self.trajectoryRawData = [ 0, 0, 0]
      self.timer.stop()
      self.startTrackingButton.text = "Start"

  def doSomething(self):

    coordinateMatrix = numpy.ones((self.n,3)) 
    self.Coordinate= self.readNeedleTipPosition()
    
    coordinateMatrix[:,0] = numpy.ones((1,self.n))*self.Coordinate[0]
    coordinateMatrix[:,1] = numpy.ones((1,self.n))*self.Coordinate[1]
    coordinateMatrix[:,2] = numpy.ones((1,self.n))*self.Coordinate[2]

    #print self.p
    #print self.Coordinate

    differenceMatrix = self.p - coordinateMatrix
    self.distanceVector = numpy.zeros((self.n,1)) 
    
    for i in xrange(self.n):
      self.distanceVector[i,0] =  numpy.sqrt(numpy.dot(differenceMatrix[i,:],differenceMatrix[i,:]))
    #print self.distanceVector 
    # Finding the minimum distance
    self.minimumValue = numpy.min(self.distanceVector)
    self.minimumValueIndex = numpy.argmin(self.distanceVector)
    #print index
    self.assignNeedleName(self.minimumValueIndex ) 
    # finding needle position versus template (Needle insterted or not)
    # first Calculate the plane of the template
    pointsForPlainMaking = self.p[0:3]
    needleTipPosition = coordinateMatrix[0]
    needleIsInside = self.isInOROut(pointsForPlainMaking,needleTipPosition)
    
    if needleIsInside == True:
      self.needleInOutLabel.setText('IN')
      self.trajectoryRawData = numpy.vstack((self.trajectoryRawData,self.Coordinate))

    elif needleIsInside == False:
      self.needleInOutLabel.setText('OUT')

      # check if the needle is out after insertion to calculate the trajectory
      if len(self.trajectoryRawData) > 10 :
        #print 'needle is out now ...'
        self.drawNeedleButton.enabled = True
        self.createNeedleTrajectory(self.trajectoryRawData)
        self.trajectoryRawData =  [ 0, 0, 0]
      else:
        needleHoleDistance = self.minimumValue 
        registrationErrorText= "%.2f" %self.minimumValue 
        if needleHoleDistance < 4: 
          self.errorStatus.setText(registrationErrorText)
        else:
          self.errorStatus.setText('..')

    #print needleIsInside

  def createFiducialMatrix(self):
    self.fiducialMatrixStatus = True
 
    # extracting the effects of transform parameters
    transformNode1 = self.templateSelector.currentNode().GetParentTransformNode()
    #print transformNode1
    shiftTransform1 = [0 , 0, 0]
    rotationTransform1 = [[1, 0,0],[0,1,0],[0,0,1]]
    #shiftTransform2 = [0, 0, 0]
    #rotationTransform2 = [1, 0,0],[0,1,0],[0,0,1]]
    if transformNode1 != None:
      m = vtk.vtkMatrix4x4()
      transformNode1.GetMatrixTransformToWorld(m)
      shiftTransform1 = [ m.GetElement(0,3), m.GetElement(1,3), m.GetElement(2,3) ]
      rotationTransform1 = [[m.GetElement(0,0), m.GetElement(0,1),m.GetElement(0,2)],[m.GetElement(1,0), m.GetElement(1,1),m.GetElement(1,2)],[m.GetElement(2,0), m.GetElement(2,1),m.GetElement(2,2)]]

    self.fids = self.inputFiducialsNodeSelector.currentNode();
    if self.fids.GetClassName() == "vtkMRMLAnnotationHierarchyNode":
    # slicer4 style hierarchy nodes
      collection = vtk.vtkCollection()
      self.fids.GetChildrenDisplayableNodes(collection)
      self.n = collection.GetNumberOfItems()

      if self.n == 0: 
        return
      self.p = numpy.zeros((self.n,3))
      for i in xrange(self.n):
        f = collection.GetItemAsObject(i)
        coords = [0,0,0]
        # Need to change to consider the transform that is applied to the points
        # offset for template width, moving the needle holes in z direction
        f.GetFiducialCoordinates(coords)
        print coords
        coords = numpy.add(coords,[ 0, 0, self.templateWidth]) 
        print coords
        self.p[i] = numpy.add(numpy.dot(rotationTransform1,coords),shiftTransform1) 
  
  def readNeedleTipPosition(self):
    
    tempFiducialsNode = self.stylusTrackerSelector.currentNode()
    #transformID = self.stylusTrackerSelector.currentNode().GetTransformNodeID()
    #transform = self.scene.GetNodeByID(transformID)
    
    m = vtk.vtkMatrix4x4()
    tempFiducialsNode.GetMatrixTransformToWorld(m)

    xCoordinate = m.GetElement(0,3)
    yCoordinate = m.GetElement(1,3)
    zCoordinate = m.GetElement(2,3)
    coordinate = [xCoordinate, yCoordinate, zCoordinate]   
    
    #print xCoordinate
    #print yCoordinate
    #print zCoordinate
    #print self.p 
    return coordinate

  def isInOROut(self,points,needleTipPosition):
    # First Calculating the Plane
    # Defining the plane through three points
    # Using Cramer's Rule
    D = points
    A = D.copy()
    B = D.copy()
    C = D.copy()
    
    A[:,0] = numpy.ones((1,3))
    B[:,1] = numpy.ones((1,3))
    C[:,2] = numpy.ones((1,3))
    detD = numpy.linalg.det(D)
    detA = numpy.linalg.det(A)
    detB = numpy.linalg.det(B)
    detC = numpy.linalg.det(C)
    d = 1
    a = -d/detD*detA
    b = -d/detD*detB
    c = -d/detD*detC
    ############
    self.a = a
    self.b = b
    self.c = c
    self.d = d
    # The needle tip 

    x = needleTipPosition[0]
    y = needleTipPosition[1]
    z = needleTipPosition[2]

    # Checking if this is the begining of the procedure
    if self.needleInsertionStarted == False:
      planeFucntionValue = a*x + b*y + c*z + d 
      self.outsideSign = numpy.sign(planeFucntionValue)
      self.needleInsertionStarted= True 
      needleIsInside = False
      #print planeFucntionValue

    elif self.needleInsertionStarted == True:
       planeFucntionValue = a*x + b*y + c*z + d 
       #print a,b,c,d
       #print planeFucntionValue
       functionValueSign = numpy.sign(planeFucntionValue)
       #print planeFucntionValue
       if functionValueSign == self.outsideSign:
         needleIsInside = False
       elif functionValueSign == -self.outsideSign:
         needleIsInside = True
    return needleIsInside
    
    # Checking in or out
  
  def createNeedleTrajectory(self,trajectoryRawData):
  # Filter Points, remove noise select the good points

    #Remove the same Nodes
    numberOfRecordedPoints = len(trajectoryRawData)
    self.trajectory =  [ 0, 0, 0]

    self.trajectory = trajectoryRawData[1]
    #print 'trajectory is:', self.trajectory
    checkPoint = self.trajectory
    #print 'needle inserted ...'
    for i in xrange(numberOfRecordedPoints-1):
      
      currentPoint = trajectoryRawData[i+1,:]
      difference = currentPoint- checkPoint
      distance = numpy.sqrt(numpy.dot(difference,difference))
      if distance > self.minimumDistanceBetweenSeperatePoints:
        
        self.trajectory = numpy.vstack((self.trajectory,currentPoint)) 
        checkPoint = currentPoint.copy()
        
    #print self.trajectory
    # Create the trajectory line
    trajectoryEdited = self.trajectory.copy()
    trajectoryNew = [0]
    for i in xrange(len(trajectoryEdited)):
      
      coordinate = trajectoryEdited [i]
      #print coordinate
      x = coordinate [0]
      y = coordinate [1]
      z = coordinate [2]
      distanceFromTemplate =  self.a*x + self.b*y + self.c*z + self.d 
      #print distanceFromTemplate 
      
      trajectoryNew.append(distanceFromTemplate)
    
    maxIndex = numpy.argmax(trajectoryNew)
    
    # only keep insertion trajectories
    self.trajectory = self.trajectory[0:maxIndex,:]
    
    #print self.trajectory 

    # Remove near point in the way back

    # Create New VTK line (model with name)

    #print 'traj calculated successfully' 
    #create the fiducial points from the needle

  def onDrawNeedleButtonClicked(self):
    
    self.progress = qt.QProgressDialog(slicer.util.mainWindow())
    self.progress.minimumDuration = 0
    self.progress.show()
    self.progress.setValue(0)
    self.progress.setMaximum(0)
    self.progress.setCancelButton(0)
    self.progress.setWindowModality(2)
 
    self.progress.setLabelText('Creating Fiducials')
    slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
    self.progress.repaint()
   
    self.drawNeedleButton.enabled = False
    print 'Please wait drawing fiducials...'

    color = [random.randrange(50,100,1)/100,random.randrange(50,100,1)/100,random.randrange(50,100,1)/100]
    #color = [0,1,0]
    for i in xrange (len(self.trajectory)):
      
      fiducial = slicer.vtkMRMLAnnotationFiducialNode()
      fiducialName = self.status.text  
      fiducialName = fiducialName
      fiducialLabel = self.status.text 
      fiducial.SetName(fiducialName)
      fiducial.SetLocked(1)
      fiducial.SetFiducialLabel(fiducialLabel)
      fiducial.SetFiducialCoordinates(self.trajectory[i])
      fiducial.Initialize(slicer.mrmlScene)
      
      
      displayNode=fiducial.GetDisplayNode()
      displayNode.SetGlyphScale(2)
      displayNode.SetColor(color)
      textNode=fiducial.GetAnnotationTextDisplayNode()
      textNode.SetTextScale(1)
      textNode.SetColor(color)

    self.progress.setValue(2)
    self.progress.repaint()
    slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
    self.progress.close()
    self.progress = None
    #print self.trajectory
    #print len(self.trajectory)

  # create a line 

  def assignNeedleName(self, index):
    if index == 0:
      self.status.setText('Ef')
    if index == 1:
      self.status.setText('Ee')
    if index == 2:
      self.status.setText('Ed')
    if index == 3:
      self.status.setText('Ec')
    if index == 4:
      self.status.setText('Dh')
    if index == 5:
      self.status.setText('Dg')
    if index == 5:
      self.status.setText('Df')
    if index == 6:
      self.status.setText('De')
    if index == 7:
      self.status.setText('Dd')
    if index == 8:
      self.status.setText('Ce')
    if index == 9:
      self.status.setText('Cn')
    if index == 10:
      self.status.setText('Cm')
    if index == 11:
      self.status.setText('Cl')
    if index == 12:
      self.status.setText('Ck')
    if index == 13:
      self.status.setText('Cj')
    if index == 14:
      self.status.setText('Ci')
    if index == 15:
      self.status.setText('Ch')
    if index == 16:
      self.status.setText('Cg')
    if index == 17:
      self.status.setText('Cf')
    if index == 18:
      self.status.setText('Ce')
    if index == 19:
      self.status.setText('Cd')
    if index == 20:
      self.status.setText('Cc')
    if index == 21:
      self.status.setText('Cb')
    if index == 22:
      self.status.setText('Ca')
    if index == 23:
      self.status.setText('Cr')
    if index == 24:
      self.status.setText('Cq')
    if index == 25:
      self.status.setText('Cp')
    if index == 26:
      self.status.setText('Co')
    if index == 27:
      self.status.setText('Bj')
    if index == 28:
      self.status.setText('Bi')
    if index == 29:
      self.status.setText('Bh')
    if index == 30:
      self.status.setText('Bg')
    if index == 31:
      self.status.setText('Bf')
    if index == 32:
      self.status.setText('Be')
    if index == 33:
      self.status.setText('Bd')
    if index == 34:
      self.status.setText('Bc')
    if index == 35:
      self.status.setText('Bb')
    if index == 36:
      self.status.setText('Ba')
    if index == 37:
      self.status.setText('Bl')
    if index == 38:
      self.status.text= 'Bk'
    if index == 39:
      self.status.setText('Dc')
    if index == 40:
      self.status.setText('Db')
    if index == 41:
      self.status.setText('Da')
    if index == 42:
      self.status.setText('Dj')
    if index == 43:
      self.status.setText('Di')
    if index == 44:
      self.status.setText('Eb')
    if index == 45:
      self.status.setText('Ea')
    if index == 46:
      self.status.setText('Eh')
    if index == 47:
      self.status.setText('Eg')

