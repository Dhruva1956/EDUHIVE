import cv2
import numpy as np
import copy
from flask import Flask, render_template, Response, request

# Initialize Flask app
app = Flask(__name__)

# Open Camera
camera = cv2.VideoCapture(0)

# Initialize variables for drawing, erasing, and color
img = np.zeros((1024, 1024, 3), np.uint8)
draw = True
erase = True
red = True
thickness = 10  # Thickness of the drawing
flag = 0

# Function to generate frames
def generate_frame():
    global img, draw, erase, red, thickness, flag

    while True:
        if flag == 0:  # TOGGLES DRAW AND ERASE FOR FIRST TIME AFTER THAT DEPENDS ON USER
            flag = 1
            draw = not draw
            erase = not erase
            red = not red

        ret, frame = camera.read()
        if not ret:
            break  # Exit if the camera feed is not retrieved

        frame = cv2.resize(frame, (1024, 1024))
        frame = cv2.bilateralFilter(frame, 5, 50, 100)  # Smoothing
        frame = cv2.flip(frame, 1)  # Horizontal Flip

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 48, 80], dtype="uint8")
        upper = np.array([20, 255, 255], dtype="uint8")
        skinMask = cv2.inRange(hsv, lower, upper)

        # Getting the contours and convex hull
        skinMask1 = copy.deepcopy(skinMask)
        contours, _ = cv2.findContours(skinMask1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if contours:  # If contours are found
            maxArea = -1
            ci = 0
            for i in range(len(contours)):
                area = cv2.contourArea(contours[i])
                if area > maxArea:
                    maxArea = area
                    ci = i

            res = contours[ci]
            hull = cv2.convexHull(res)

            # Moments for centroid calculation
            M = cv2.moments(res)
            cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
            cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0

            # Getting extreme points
            extLeft = tuple(res[res[:, :, 0].argmin()][0])
            extRight = tuple(res[res[:, :, 0].argmax()][0])
            extTop = tuple(res[res[:, :, 1].argmin()][0])
            extBot = tuple(res[res[:, :, 1].argmax()][0])

            # Draw contours and points
            cv2.drawContours(frame, [res], -1, (0, 255, 0), 2)
            cv2.drawContours(frame, [hull], -1, (0, 0, 255), 3)
            cv2.circle(frame, extLeft, 8, (0, 0, 255), -1)
            cv2.circle(frame, extRight, 8, (0, 255, 0), -1)
            cv2.circle(frame, extTop, 8, (100, 55, 100), -1)
            cv2.circle(frame, extBot, 8, (255, 255, 0), -1)
            cv2.circle(frame, (cX, cY), 7, (255, 255, 255), -1)
            cv2.putText(frame, "center", (cX - 20, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Draw on the image if drawing is enabled
            if draw:
                cv2.circle(img, extTop, thickness, (255, 255, 255), -1)  # Draw circle at fingertip position
            if erase:
                cv2.circle(img, extTop, thickness, (0, 0, 0), 7)  # Erase circle at fingertip position
            if red:
                cv2.circle(img, extTop, thickness, (0, 0, 255), -1)  # Draw red circle at fingertip position

        # Combine the canvas with the frame
        combined_frame = cv2.addWeighted(frame, 0.7, img, 0.3, 0)

        # Convert to JPEG format for streaming
        ret, jpeg = cv2.imencode('.jpg', combined_frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_draw', methods=['POST'])
def toggle_draw():
    global draw
    draw = not draw
    return 'OK'

@app.route('/toggle_erase', methods=['POST'])
def toggle_erase():
    global erase
    erase = not erase
    return 'OK'

@app.route('/toggle_red', methods=['POST'])
def toggle_red():
    global red
    red = not red
    return 'OK'

# Route to reset the canvas
@app.route('/toggle_canvas', methods=['POST'])
def toggle_canvas():
    global img
    # Reset the canvas to a blank image
    img = np.zeros((1024, 1024, 3), np.uint8)
    return '', 204  # Return a 'No Content' response to indicate success

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
