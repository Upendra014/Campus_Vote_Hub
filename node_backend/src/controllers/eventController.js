const Event = require('../models/Event');
const AppError = require('../utils/AppError');
const catchAsync = require('../utils/catchAsync');

exports.getAllEvents = catchAsync(async (req, res, next) => {
  const events = await Event.find().populate('createdBy', 'name');

  res.status(200).json({
    success: true,
    results: events.length,
    data: {
      events,
    },
  });
});

exports.getEvent = catchAsync(async (req, res, next) => {
  const event = await Event.findById(req.params.id).populate('createdBy', 'name');

  if (!event) return next(new AppError(404, 'No event found with that ID'));

  res.status(200).json({
    success: true,
    data: {
      event,
    },
  });
});

exports.createEvent = catchAsync(async (req, res, next) => {
  const newEvent = await Event.create({
    name: req.body.name,
    description: req.body.description,
    createdBy: req.user.id,
  });

  res.status(201).json({
    success: true,
    data: {
      event: newEvent,
    },
  });
});

exports.updateEvent = catchAsync(async (req, res, next) => {
  const event = await Event.findByIdAndUpdate(req.params.id, req.body, {
    new: true,
    runValidators: true,
  });

  if (!event) return next(new AppError(404, 'No event found with that ID'));

  res.status(200).json({
    success: true,
    data: {
      event,
    },
  });
});

exports.deleteEvent = catchAsync(async (req, res, next) => {
  const event = await Event.findByIdAndDelete(req.params.id);

  if (!event) return next(new AppError(404, 'No event found with that ID'));

  res.status(204).json({
    success: true,
    data: null,
  });
});
