import cv2
import numpy
import time

class CaptureManager(object):

    def __init__(self,capture,previewWindowManager=None,shouldMirrorPreview=False):
        
        self.previewWindowManager = previewWindowManager
        self.shouldMirrorPreview = shouldMirrorPreview

        self._capture = capture
        self._channel = 0
        self._enteredFrame = False
        self._frame = None 
        self._imageFilename = None
        self._videoFilename = None
        self._videoEncoding = None
        self._videoWriter = None
        
        self._startTime = None
        self._framesElapsed = int(0)
        self._fpsEstimate = None
    
    @property
    def channel(self):
        return self._channel
    
    @channel.setter
    def channel(self,value):
        if self._channel != value:
            self._channel = value
            self._frame = None
    @property
    def frame(self):
        if self._enteredFrame and self._frame is None:
            _,self._frame = self._capture.retrieve()#channel = self.channel)
        
        return self._frame

    @property
    def isWritingImage(self):
        return self._imageFilename is not None

    @property
    def isWritingVideo(self):
        return self._videoFilename is not None
    
    def enterFrame(self):
        """Capture the next frame, if any"""
        
        #But first, check that any previous frame was exited
        assert not self._enteredFrame, 'previous enterFrame() had no matching exitFrame()'

        if self._capture is not None:
            self._enteredFrame = self._capture.grab() #Bool

    def exitFrame(self):
        """Draw to the window. Write to files. Release the frame"""

        #check whether any grabbed frame is retrievable
        #the getter may retrieve and cache the frame
        if self.frame is None:
            self._enteredFrame = False
            return
        
        #Update the FPS estimate and related variables
        if self._framesElapsed == 0:
            self._startTime = time.time()
        else:
            timeElapsed = time.time() - self._startTime
            self._fpsEstimate = self._framesElapsed/timeElapsed
        self._framesElapsed += 1

        #Draw to the window, if any.
        if self.previewWindowManager is not None:
            recFrame = self._frame
            if self.isWritingVideo:
                recFrame = self._drawRecSymbol()
            if self.shouldMirrorPreview:
                mirroredFrame = numpy.fliplr(recFrame).copy()
                self.previewWindowManager.show(mirroredFrame)
            else:
                self.previewWindowManager.show(recFrame)

        #Write to the image file, if any.
        if self.isWritingImage:
            cv2.imwrite(self._imageFilename,self._frame)
            self._imageFilename = None

        #Write to the video file, if any.
        self._writeVideoFrame()
        
        #Release the frame
        self._frame = None
        self._enteredFrame = False
    
    def writeImage(self, filename):
        """Write the next exited frame to an image file"""
        self._imageFilename= filename
    
    def startWritingVideo(self, filename, encoding = cv2.VideoWriter_fourcc('I','4','2','0')):#cv2.CV_FOURCC('I','4','2','0')):
        """ Start writing exited frames to a video file"""
        self._videoFilename = filename
        self._videoEncoding = encoding

    def stopWritingVideo(self):
        """Stop writing exited frame to a video file"""
        self._videoFilename = None
        self._videoEncoding = None
        self._videoWriter = None
    
    def _drawRecSymbol(self):
        size = (int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        radius = int(size[0]/70)
        x = int(radius*1.5)
        y = int(radius*1.5)
        circle_img = cv2.circle(self._frame.copy(),(x,y),radius,color=(0,0,255),thickness=-1)
        return cv2.putText(circle_img,"REC",(x-radius,y+radius),cv2.FONT_HERSHEY_PLAIN,fontScale=1,color=(0,0,0),thickness=2,bottomLeftOrigin=True)

    def _writeVideoFrame(self):
        if not self.isWritingVideo:
            return
        if self._videoWriter is None:
            fps = self._capture.get(cv2.CAP_PROP_FPS)
            if fps == 0.0:
                #the capture's FPS is unknown so use an estimate
                if self._framesElapsed < 20:
                    #wait untile more frames elapse so that te estimate is more stable
                    return
                else:
                    fps = self._fpsEstimate
            size = (int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            self._videoWriter = cv2.VideoWriter(self._videoFilename,self._videoEncoding,fps,size)
        self._videoWriter.write(self._frame)

class WindowManager(object):

    def __init__(self,windowName,keypressCallback = None):
        self.keypressCallback = keypressCallback
        self._windowName = windowName
        self._isWindowCreated = False

    @property
    def isWindowCreated(self):
        return self._isWindowCreated
    
    def createWindow(self):
        cv2.namedWindow(self._windowName)
        self._isWindowCreated = True

    def show(self,frame):
        cv2.imshow(self._windowName,frame)
   
    def destroyWindow(self):
        cv2.destroyWindow(self._windowName)
        self._isWindowCreated = False
    
    def processEvents(self):
        keycode = cv2.waitKey(1)
        if self.keypressCallback is not None and keycode != -1:
            #discard any non-ASCII info encoded by GTK
            keycode &= 0xFF
            self.keypressCallback(keycode)
    