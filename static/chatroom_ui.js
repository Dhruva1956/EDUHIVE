var myVideo;
var screenStream;
var audioMuted = false;
var videoMuted = false;

document.addEventListener("DOMContentLoaded", (event) => {
    myVideo = document.getElementById("local_vid");
    myVideo.onloadeddata = () => {
        console.log("W,H: ", myVideo.videoWidth, ", ", myVideo.videoHeight);
    };
    
    var muteBttn = document.getElementById("bttn_mute");
    var muteVidBttn = document.getElementById("bttn_vid_mute");
    var callEndBttn = document.getElementById("call_end");
    var shareScreenBttn = document.getElementById("bttn_share_screen");

    muteBttn.addEventListener("click", (event) => {
        audioMuted = !audioMuted;
        setAudioMuteState(audioMuted);
    });

    muteVidBttn.addEventListener("click", (event) => {
        videoMuted = !videoMuted;
        setVideoMuteState(videoMuted);
    });

    callEndBttn.addEventListener("click", (event) => {
        window.location.replace("/login");
    });

    shareScreenBttn.addEventListener("click", startScreenShare);

    document.getElementById("room_link").innerHTML = `or the link: <span class="heading-mark">${window.location.href}</span>`;
});

function startScreenShare() {
    if (screenStream) {
        stopScreenShare();
        return;
    }

    navigator.mediaDevices.getDisplayMedia({ video: true }).then((stream) => {
        screenStream = stream;
        
        // Set the screen stream to the myVideo element
        myVideo.srcObject = screenStream;

        // Broadcast the screen stream to all peers
        broadcastScreenStream(screenStream);

        // Add event listener to detect when screen sharing ends
        screenStream.getVideoTracks()[0].addEventListener("ended", stopScreenShare);

        // Update button text/icon
        document.getElementById("bttn_share_screen").innerText = "Stop Sharing";
    }).catch((error) => {
        console.error("Error sharing screen: ", error);
    });
}

function stopScreenShare() {
    if (!screenStream) return;

    // Stop the screen share tracks
    screenStream.getTracks().forEach((track) => track.stop());
    screenStream = null;

    // Revert back to the webcam stream on myVideo
    navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then((stream) => {
        myVideo.srcObject = stream;

        // Broadcast the original webcam stream back to peers
        broadcastScreenStream(stream);

        // Update button text/icon
        document.getElementById("bttn_share_screen").innerText = "Share Screen";
    }).catch((error) => {
        console.error("Error accessing webcam after stopping screen share:", error);
    });
}


function makeVideoElement(element_id, display_name) {
    let wrapper_div = document.createElement("div");
    let vid_wrapper = document.createElement("div");
    let vid = document.createElement("video");
    let name_text = document.createElement("div");

    wrapper_div.id = "div_" + element_id;
    vid.id = "vid_" + element_id;

    wrapper_div.className = "shadow video-item";
    vid_wrapper.className = "vid-wrapper";
    name_text.className = "display-name";

    vid.autoplay = true;
    vid.controls = true;
    name_text.innerText = display_name;

    vid_wrapper.appendChild(vid);
    wrapper_div.appendChild(vid_wrapper);
    wrapper_div.appendChild(name_text);

    return wrapper_div;
}

function addVideoElement(element_id, display_name) {
    document.getElementById("video_grid").appendChild(makeVideoElement(element_id, display_name));
}

function removeVideoElement(element_id) {
    let v = getVideoObj(element_id);
    if (v.srcObject) {
        v.srcObject.getTracks().forEach(track => track.stop());
    }
    v.removeAttribute("srcObject");
    v.removeAttribute("src");

    document.getElementById("div_" + element_id).remove();
}

function getVideoObj(element_id) {
    return document.getElementById("vid_" + element_id);
}

function setAudioMuteState(flag) {
    let local_stream = myVideo.srcObject;
    local_stream.getAudioTracks().forEach((track) => {
        track.enabled = !flag;
    });
    // switch button icon
    document.getElementById("mute_icon").innerText = (flag) ? "mic_off" : "mic";
}

function setVideoMuteState(flag) {
    let local_stream = myVideo.srcObject;
    local_stream.getVideoTracks().forEach((track) => {
        track.enabled = !flag;
    });
    // switch button icon
    document.getElementById("vid_mute_icon").innerText = (flag) ? "videocam_off" : "videocam";
}

function broadcastScreenStream(stream) {
    // Assuming `peers` is an array of connected peer connections
    for (const peer of peers) {
        const sender = peer.getSenders().find(s => s.track.kind === "video");
        
        // Replace the current video track with the screen share track
        if (sender) {
            sender.replaceTrack(stream.getVideoTracks()[0]);
        } else {
            // If no video sender is available, add the screen track
            stream.getTracks().forEach(track => peer.addTrack(track, stream));
        }
    }
}
