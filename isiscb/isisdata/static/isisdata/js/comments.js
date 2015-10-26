var app = angular.module('commentsApp', ['ngResource', 'ui.bootstrap']);

app.config(function($httpProvider, $resourceProvider){
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    $resourceProvider.defaults.stripTrailingSlashes = false;
});

app.factory('Comment', function($resource) {
    return $resource('/rest/comment/:id/', {
        id: '@_id',
        subject_content_type: SUBJECT_CONTENT_TYPE,
        subject_instance_id: SUBJECT_INSTANCE_ID
     }, {
        list: {
            method: 'GET',
            cache: true,
            headers: {'Content-Type': 'application/json'},
            params: {
                subject_content_type: SUBJECT_CONTENT_TYPE,
                subject_instance_id: SUBJECT_INSTANCE_ID
            }
        },
        save: {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            params: {
                subject_content_type: SUBJECT_CONTENT_TYPE,
                subject_instance_id: SUBJECT_INSTANCE_ID
            }
        },
        get: {
            method: 'GET',
            headers: {'Content-Type': 'application/json'},
        },
        update: {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
        }

    });
});

app.controller('CommentController', ['$scope', 'Comment', function($scope, Comment) {
    $scope.comments = [];
    $scope.noscroll = false;

    $scope.updateComments = function() {
        return Comment.query().$promise.then(function(comments) {
            $scope.comments = comments;
            comments.forEach(function(comment) {
                comment.editing = false;
            });
            return comments;
        });
    }
    $scope.updateComments();

    $scope.updateComment = function(comment) {
        comment.editing = false;
        Comment.get({id:comment.id}, function(c) {
            c.text = comment.text;
            c.$update({id:c.id}).then(function(){
                $scope.noscroll = true;
                $scope.updateComments();
            });
        });
    };

    $scope.edit = function(comment, user_id) {
        $scope.comments.forEach(function(otherComment) {
            otherComment.editing = false;
        });
        if ($scope.canEdit(comment)) {
            comment.editing = true;
        }
    }

    $scope.canEdit = function(comment) {
        if (USER_ID == undefined) {
            return false;
        }
        return (USER_ID == comment.created_by.id);
    }

    $scope.submitComment = function() {
        var data = {
            text: $scope.commentText,
            subject_instance_id: SUBJECT_INSTANCE_ID,
            subject_content_type: SUBJECT_CONTENT_TYPE
        }

        comment = new Comment(data);
        comment.$save().then(function() {
            $scope.commentText = '';
            $scope.updateComments();
        });
    }

    $scope.$watch("comments", function() {
        if (!$scope.noscroll) {
            $('.comment-body').scrollTop($('.comment-body')[0].scrollHeight);
        }
        $scope.noscroll = false;
    });

}]);

app.filter('unsafe', function($sce) {
    return function(val) {
        return $sce.trustAsHtml(val);
    };
});
