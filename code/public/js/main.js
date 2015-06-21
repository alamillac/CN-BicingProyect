var Main = (function() {

    var _private = {
        options: null,
        maxTimeInterval: 2000,
        minTimeInterval: 100,
        timeInterval: 500,
        current_image: 0,
        num_images: 0,
        intervalFunctionId: null,

        run: function() {
            if(!_private.intervalFunctionId) {
                var that = this;
                _private.intervalFunctionId = setInterval(function() {
                    _private.update_images(that.options.images_data, _private.current_image);
                    _private.current_image += 1;
                    _private.current_image %= _private.num_images;
                }, _private.timeInterval);
            }
        },

        update_images: function(images_data, current_image) {
            for(var i = 0; i<images_data.length; i++) {
                _private.image_handler(images_data[i], current_image);
            }
        },

        initEvents: function() {
            $(_private.options.controls.sel.fbackward).on('click', _private.fbackward);
            $(_private.options.controls.sel.backward).on('click', _private.backward);
            $(_private.options.controls.sel.play_pause).on('click', _private.play_pause);
            $(_private.options.controls.sel.forward).on('click', _private.forward);
            $(_private.options.controls.sel.fforward).on('click', _private.fforward);
            $(_private.options.controls.sel.speed).on('change', _private.speedHandler);
        },

        speedHandler: function(event) {
            var speed = this.value;
            var max_speed = this.max;
            var min_speed = this.min;
            _private.setSpeed(speed, max_speed, min_speed);
        },

        initSpeed: function() {
            var $speed = $(_private.options.controls.sel.speed);
            var speed = $speed.val();
            var max_speed = $speed.attr('max');
            var min_speed = $speed.attr('min');
            _private.setSpeed(speed, max_speed, min_speed);
        },

        setSpeed: function(speed, max_speed, min_speed) {
            var m = (_private.maxTimeInterval - _private.minTimeInterval)/(min_speed - max_speed);
            var b = (_private.maxTimeInterval - m * min_speed);
            var interval = m * speed + b;
            _private.timeInterval = interval;
            //update interval
            console.log("Setting delay to " + interval + " ms");
            if(_private.intervalFunctionId) {
                clearInterval(_private.intervalFunctionId);
                _private.intervalFunctionId = null;
                _private.run();
            }
        },

        fbackward: function() {
            _private.current_image = 0;
            _private.update_images(_private.options.images_data, _private.current_image);
        },

        backward: function() {
            if(_private.current_image > 0) {
                _private.current_image -= 1;
                _private.update_images(_private.options.images_data, _private.current_image);
            }
        },

        fforward: function() {
            _private.current_image = _private.num_images - 1;
            _private.update_images(_private.options.images_data, _private.current_image);
        },

        forward: function() {
            if(_private.current_image < _private.num_images - 1) {
                _private.current_image += 1;
                _private.update_images(_private.options.images_data, _private.current_image);
            }
        },

        play_pause: function(event) {
            $button = $(this);
            if($button.hasClass('_play')) {
                //set icon class
                $button.removeClass('_play');
                $button.addClass('_pause');
                $icon = $button.find('i');
                $icon.removeClass(_private.options.controls.play_class);
                $icon.addClass(_private.options.controls.pause_class);
                //play images
                _private.run();
                //disable the rest of buttons
                $(_private.options.controls.sel.fbackward).prop('disabled', true);
                $(_private.options.controls.sel.backward).prop('disabled', true);
                $(_private.options.controls.sel.forward).prop('disabled', true);
                $(_private.options.controls.sel.fforward).prop('disabled', true);
            }
            else {
                //set icon class
                $button.removeClass('_pause');
                $button.addClass('_play');
                $icon = $button.find('i');
                $icon.removeClass(_private.options.controls.pause_class);
                $icon.addClass(_private.options.controls.play_class);
                //pause images
                if(_private.intervalFunctionId) {
                    clearInterval(_private.intervalFunctionId);
                    _private.intervalFunctionId = null;
                }
                //enable the rest of buttons
                $(_private.options.controls.sel.fbackward).prop('disabled', false);
                $(_private.options.controls.sel.backward).prop('disabled', false);
                $(_private.options.controls.sel.forward).prop('disabled', false);
                $(_private.options.controls.sel.fforward).prop('disabled', false);
            }
        },

        image_handler: function(image_data, current_image) {
            var str_num_image = ("000" + current_image).slice(-4);
            var image_name = image_data.image_prefix + str_num_image + '.png';
            var src_image = image_data.image_dir + '/' + image_name;
            $('#'+image_data.id).attr('src', src_image);
        }
    };

    var _public = {
        init: function(options) {
            _private.options = options;
            _private.num_images = options.num_images;
            _private.initEvents();
            _private.fbackward();
            _private.initSpeed();
        }
    };

    return _public;
})();
