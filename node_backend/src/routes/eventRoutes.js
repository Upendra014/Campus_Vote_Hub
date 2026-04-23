const express = require('express');
const eventController = require('../controllers/eventController');
const { protect, restrictTo } = require('../middlewares/auth');

const router = express.Router();

// Public routes for reading events
router.get('/', eventController.getAllEvents);
router.get('/:id', eventController.getEvent);

// Protected routes for admins/coordinators to manage events
router.use(protect);
router.use(restrictTo('admin', 'coordinator'));

router.post('/', eventController.createEvent);
router.patch('/:id', eventController.updateEvent);
router.delete('/:id', eventController.deleteEvent);

module.exports = router;
