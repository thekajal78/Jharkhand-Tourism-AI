import React from 'react';
import { Box, Container, Typography } from '@mui/material';

const Footer: React.FC = () => {
  return (
    <Box component="footer" sx={{ bgcolor: 'primary.main', color: 'white', py: 3, mt: 'auto' }}>
      <Container maxWidth="lg">
        <Typography variant="body2" align="center">
          © 2024 Jharkhand Tourism AI Platform. Made with ❤️ for Jharkhand Tourism.
        </Typography>
      </Container>
    </Box>
  );
};

export default Footer;