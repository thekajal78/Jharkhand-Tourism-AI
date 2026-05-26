import React from 'react';
import { Container, Typography, Box, Button, Grid, Card, CardContent } from '@mui/material';

const HomePage: React.FC = () => {
  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 8 }}>
        {/* Hero Section */}
        <Box textAlign="center" mb={8}>
          <Typography variant="h1" component="h1" gutterBottom>
            Discover Jharkhand with AI
          </Typography>
          <Typography variant="h5" color="text.secondary" paragraph>
            Experience the beauty of Jharkhand through AI-powered recommendations and visual search
          </Typography>
          <Button variant="contained" size="large" sx={{ mr: 2 }}>
            Explore Destinations
          </Button>
          <Button variant="outlined" size="large">
            Start Visual Search
          </Button>
        </Box>

        {/* Feature Cards */}
        <Grid container spacing={4}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  🤖 AI Recommendations
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Get personalized travel suggestions based on your preferences and behavior.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  📸 Visual Search
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Upload photos to find similar destinations using our CLIP-powered image search.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  💬 Smart Chatbot
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Get instant help in multiple languages with our AI-powered travel assistant.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
};

export default HomePage;