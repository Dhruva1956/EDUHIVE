let socket = io.connect('http://' + document.domain + ':' + location.port);

$(document).ready(function() {
    $('.tutor-link').click(function() {
        const tutorId = $(this).data('tutor-id');
        $('#current-tutor').text(tutorId);
        $('#chat-window').show();
        $('#chat').val(''); // Clear chat window
    });

    $('.student-link').click(function() {
        const studentId = $(this).data('student-id');
        $('#current-student').text(studentId);
        $('#chat-window').show();
        $('#chat').val(''); // Clear chat window
    });

    $('#send').click(function() {
        const message = $('#message').val();
        const currentId = $('#current-tutor').text() || $('#current-student').text();
        if (message) {
            socket.emit('send_message', {msg: message, to: currentId});
            $('#message').val(''); // Clear message input
        }
    });

    socket.on('receive_message', function(data) {
        $('#chat').val($('#chat').val() + data.msg + '\n');
    });
});
