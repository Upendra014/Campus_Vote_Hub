const mongoose = require('mongoose');

const eventSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, 'An event must have a name'],
      unique: true,
      trim: true,
      maxlength: 100,
      index: true,
    },
    description: {
      type: String,
      required: [true, 'An event must have a description'],
    },
    votes: {
      type: Number,
      default: 0,
    },
    createdBy: {
      type: mongoose.Schema.ObjectId,
      ref: 'User',
      required: [true, 'An event must belong to a user'],
      index: true,
    },
    isActive: {
      type: Boolean,
      default: true,
    },
  },
  {
    timestamps: true,
  }
);

const Event = mongoose.model('Event', eventSchema);
module.exports = Event;
