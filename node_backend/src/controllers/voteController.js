const Vote = require('../models/Vote');
const Event = require('../models/Event');
const AppError = require('../utils/AppError');
const catchAsync = require('../utils/catchAsync');

exports.castVote = catchAsync(async (req, res, next) => {
  const { eventId } = req.body;
  const userId = req.user.id;
  const ipAddress = req.ip || req.connection.remoteAddress;

  // 1) Verify the event exists and is active
  const event = await Event.findById(eventId);
  if (!event) {
    return next(new AppError(404, 'Event not found'));
  }
  if (!event.isActive) {
    return next(new AppError(400, 'This event is no longer active'));
  }

  // 2) Try to create a vote
  // Unique index on [event, user] in the model will naturally reject duplicates!
  try {
    const vote = await Vote.create({
      user: userId,
      event: eventId,
      ipAddress,
    });

    // 3) Atomic increment for the event vote count
    event.votes = event.votes + 1;
    await event.save({ validateBeforeSave: false });

    res.status(201).json({
      success: true,
      data: {
        vote,
      },
    });
  } catch (err) {
    if (err.code === 11000) {
      // 11000 is Mongo's duplicate key error
      return next(new AppError(400, 'You have already voted for this event'));
    }
    throw err; // Send other errors to the global error handler
  }
});
