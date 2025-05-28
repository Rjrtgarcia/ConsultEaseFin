    def _load_faculty_image(self):
        pixmap_loaded = False
        # Assume self.faculty.get_image_path() returns an absolute, verified path or None
        image_path = self.faculty.get_image_path() if hasattr(self.faculty, 'get_image_path') else None

        if image_path: # If model provides a valid path
            try:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap)
                    pixmap_loaded = True
                else:
                    logger.warning(f"Could not load image for faculty {self.faculty.name} from provided path: {image_path} (pixmap isNull)")
            except Exception as e:
                logger.error(f"Error loading faculty image for {self.faculty.name} from {image_path}: {str(e)}")
        
        if not pixmap_loaded:
            # Fallback to default icon
            try:
                # Assuming IconProvider.get_icon returns a QIcon object
                default_qicon = IconProvider.get_icon(Icons.USER) 
                if default_qicon and not default_qicon.isNull():
                    self.image_label.setPixmap(default_qicon.pixmap(QSize(60, 60))) # Specify size for pixmap
                    # pixmap_loaded = True # Not strictly needed to set true here as it's a fallback
                else:
                    logger.warning(f"Default user icon (Icons.USER) could not be loaded or is null. Using theme placeholder for {self.faculty.name}.")
                    fallback_pixmap = QPixmap(QSize(60, 60))
                    fallback_pixmap.fill(QColor(self.theme.BG_SECONDARY)) 
                    self.image_label.setPixmap(fallback_pixmap)
            except Exception as e:
                logger.error(f"Exception while trying to load default user icon for {self.faculty.name}: {str(e)}")
                fallback_pixmap = QPixmap(QSize(60, 60))
                fallback_pixmap.fill(QColor(self.theme.BG_SECONDARY))
                self.image_label.setPixmap(fallback_pixmap) 