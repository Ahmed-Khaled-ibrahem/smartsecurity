part of 'app_cubit.dart';

sealed class AppState extends Equatable {
  const AppState();
}

final class AppInitial extends AppState {
  @override
  List<Object> get props => [];
}

final class Refresh extends AppState {
  @override
  List<Object> get props => [];
}

final class RefreshExtend extends AppState {
  @override
  List<Object> get props => [];
}

