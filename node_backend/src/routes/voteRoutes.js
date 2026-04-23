const express = require('express');
const voteController = require('../controllers/voteController');
const { protect } = require('../middlewares/auth');

const router = express.Router();

router.use(protect);

router.post('/', voteController.castVote);

module.exports = router;
