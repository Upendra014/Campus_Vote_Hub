const mongoose = require('mongoose');

const voteSchema = new mongoose.Schema(
  {
    user: {
      type: mongoose.Schema.ObjectId,
      ref: 'User',
      required: [true, 'A vote must belong to a user'],
    },
    event: {
      type: mongoose.Schema.ObjectId,
      ref: 'Event',
      required: [true, 'A vote must belong to an event'],
    },
    ipAddress: {
      type: String,
    },
  },
  {
    timestamps: true,
  }
);

// Prevent a user from voting multiple times on the same event
voteSchema.index({ event: 1, user: 1 }, { unique: true });

const Vote = mongoose.model('Vote', voteSchema);
module.exports = Vote;
