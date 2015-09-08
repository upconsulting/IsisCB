var app = angular.module('commentsApp', ['ngResource', 'ui.bootstrap']);

app.config(function($httpProvider, $resourceProvider){
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    $resourceProvider.defaults.stripTrailingSlashes = false;
});

app.factory('Comment', function($resource) {
    return $resource('/rest/comment/:id/', {
        subject_content_type: SUBJECT_CONTENT_TYPE,
        subject_instance_id: SUBJECT_INSTANCE_ID
    }, {
        list: {
            method: 'GET',
            cache: true,
            headers: {'Content-Type': 'application/json'}
        },
        save: {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        }
    });
});

app.controller('CommentController', ['$scope', 'Comment', function($scope, Comment) {
    $scope.comments = [];

    $scope.updateComments = function() {
        return Comment.query().$promise.then(function(comments) {
            $scope.comments = comments;
            return comments;
        });
    }
    $scope.updateComments();

    $scope.submitComment = function() {
        var data = {
            text: $scope.commentText,
            subject_instance_id: SUBJECT_INSTANCE_ID,
            subject_content_type: SUBJECT_CONTENT_TYPE
        }
        console.log(data);
        comment = new Comment(data);
        comment.$save().then(function() {
            $scope.commentText = '';
            $scope.updateComments();
        });
    }

    $scope.$watch("comments", function() {
        $('.comment-body').scrollTop($('.comment-body')[0].scrollHeight);
    });

}]);
